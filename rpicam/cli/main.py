"""Console script for rpicam."""
import sys
import click


from . import click_option


@click.group(
    short_help='Servo controls.', context_settings=dict(help_option_names=["-h", "--help"])
)
def servo(args=None):
    pass


@click.group(
    short_help='Recording functions.', context_settings=dict(help_option_names=["-h", "--help"])
)
def cam(args=None):
    pass


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
def cli(args=None):
    pass


cli.add_command(cam)
cli.add_command(servo)


@servo.command('move', short_help='Move a servo using pre-defined commands.')
@click_option('-p', '--pin', type=int, default=7, help='The BOARD pin connected to the servo.')
@click_option('-c', '--cycle', is_flag=True, help='Whether to cycle the given command sequence.')
@click.argument('ops', type=str, nargs=-1)
def move(ops, pin, cycle):
    from rpicam.servo import Servo, parse_servo_op

    ops = [parse_servo_op(x) for x in ops]
    s = Servo(pin, verbose=True)
    s.execute_sequence(ops, cycle=cycle)


@cam.command('live', short_help='Display a live video stream.')
@click_option('-s', '--spf', type=float, default=0.5, help='Seconds per frame.')
@click_option('--servo_pin_ad', type=int, default=7, help='Servo pin for AD axis.')
@click_option('--servo_pin_ws', type=int, default=None, help='Servo pin for WS axis.')
def live(spf, servo_pin_ad, servo_pin_ws):
    from time import sleep
    from rpicam.cams import LivePreviewCam
    from rpicam.platform import Platform
    from rpicam.servo import Servo
    from rpicam.servo import ServoOpParser

    try:
        lpc = LivePreviewCam()
        lpc_args = dict(spf=spf)
        servos = dict(
            servo_ad=Servo(servo_pin_ad, verbose=True, servo_name='A/D', on_invalid_angle='ignore')
        )
        if servo_pin_ws:
            servo_name_ws = 'servo_ws'
            servos[servo_name_ws] = Servo(
                servo_pin_ws, verbose=True, servo_name='W/S', on_invalid_angle='ignore'
            )
        else:
            servo_name_ws = None
        p = Platform(cam=lpc, servos=servos, verbose=True)
        p.start_recording(**lpc_args)
        while True:
            sleep(0.01)
            wasd = ServoOpParser.interpret_wasd(
                servo_name_ad='servo_ad', servo_name_ws=servo_name_ws
            )
            if wasd is not None:
                p.submit_servo_sequence(wasd[0], [wasd[1]])

    except KeyboardInterrupt:
        pass


@cam.command('timelapse', short_help='Create a timelapse video.')
@click_option(
    '-d', '--duration', type=int, default=120, help='The total recording duration in min.'
)
@click_option('-s', '--spf', type=int, default=10, help='The time between frames in seconds.')
@click_option(
    '-f', '--fps', type=int, default=30, help='The number of frames per second in the final video.'
)
@click_option(
    '-r',
    '--resolution',
    type=int,
    nargs=2,
    help='The resolution of the video (width, height) in px.',
)
@click_option(
    '-o',
    '--outfile',
    type=click.Path(dir_okay=False, exists=False),
    help='The path to write the output file to.',
)
@click_option(
    '--servo_ops',
    type=str,
    default=None,
    help='A space-delimited string of servo operations to perform during timelapse recording. Optional.',
)
@click_option(
    '--servo_pin',
    type=int,
    default=7,
    help='The pin on which the servo is connected. Only required if servo_ops are supplied.',
)
@click_option(
    '--cycle_servo_ops',
    is_flag=True,
    help='Whether to cycle the given servo operations during timelapse recording.',
)
def timelapse(duration, spf, fps, resolution, outfile, servo_ops, servo_pin, cycle_servo_ops):
    from datetime import timedelta
    from rpicam.cams import TimelapseCam, AnnotateFrameWithDt
    from rpicam.platform import Platform
    from rpicam.servo import Servo
    from rpicam.servo import ServoOpParser

    cam = TimelapseCam(
        callbacks=[AnnotateFrameWithDt()],
        verbose=True,
        camera_rotation=0,
        resolution=resolution,
    )
    cam_args = dict(
        fps=fps,
        duration=timedelta(minutes=duration),
        sec_per_frame=spf,
        outfile=outfile,
    )
    if servo_ops:
        servo = Servo(servo_pin, verbose=True)
        servo_ops = servo_ops.split(' ')
        servo._logger.info(
            f'Will execute sequence: {servo_ops}{", cycling" if cycle_servo_ops else ""}'
        )
        servo_ops = [ServoOpParser.parse_servo_op(x) for x in servo_ops]

        p = Platform(cam=cam, servos={'s': servo}, verbose=True)
        p.start_recording(**cam_args)
        p.submit_servo_sequence(servo_name='s', sequence=servo_ops, cycle=cycle_servo_ops)
        p.poll_cam_result()
    else:
        cam.record(**cam_args)


def main():
    cli()


if __name__ == "__main__":
    main()
