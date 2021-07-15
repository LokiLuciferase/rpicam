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


def default_servo_args(f):
    f = click_option(
        '--init_angle',
        type=str,
        default=0,
        help='The initial angle for the servo. Valid choices are "load" from semi-persistent state (gets cleared at reboot), or the integer describing the angle.',
    )(f)
    return f


@servo.command('move', short_help='Move a servo using pre-defined commands.')
@click_option('-p', '--pin', type=int, default=7, help='The BOARD pin connected to the servo.')
@click_option('-c', '--cycle', is_flag=True, help='Whether to cycle the given command sequence.')
@default_servo_args
@click.argument('ops', type=str, nargs=-1)
def move(ops, pin, cycle, init_angle, *args, **kwargs):
    from rpicam.servo import Servo, ServoOpParser
    from rpicam.utils.state import State

    ops = [ServoOpParser.parse_servo_op(x) for x in ops]
    s = Servo(pin, verbose=True, init_angle=init_angle)
    s.execute_sequence(ops, cycle=cycle)
    s.write_servo_angle(State())


@cam.command('live', short_help='Display a live video stream.')
@click_option('-s', '--spf', type=float, default=0.5, help='Seconds per frame.')
@click_option('--servo_pin_ad', type=int, default=7, help='Servo pin for AD axis.')
@click_option('--servo_pin_ws', type=int, default=None, help='Servo pin for WS axis.')
@default_servo_args
def live(spf, servo_pin_ad, servo_pin_ws, init_angle, *args, **kwargs):
    from time import sleep
    from rpicam.cams import LivePreviewCam
    from rpicam.platform import Platform
    from rpicam.servo import Servo, ServoOpParser
    from rpicam.utils.state import State

    try:
        lpc = LivePreviewCam()
        lpc_args = dict(spf=spf)
        servos = dict(
            servo_ad=Servo(
                servo_pin_ad,
                verbose=True,
                servo_name='A/D',
                on_invalid_angle='ignore',
                init_angle=init_angle,
            )
        )
        if servo_pin_ws:
            servo_name_ws = 'servo_ws'
            servos[servo_name_ws] = Servo(
                servo_pin_ws, verbose=True, servo_name='W/S', on_invalid_angle='ignore', init_angle=init_angle
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

    finally:
        for k in servos:
            servos[k].write_servo_angle(State())


def _timelapse(
    duration,
    spf,
    fps,
    resolution,
    outfile,
    servo_ops,
    servo_pin,
    cycle_servo_ops,
    init_angle,
    *args,
    **kwargs,
):
    from datetime import timedelta
    from rpicam.cams import TimelapseCam, AnnotateFrameWithDt
    from rpicam.platform import Platform
    from rpicam.servo import Servo
    from rpicam.servo import ServoOpParser
    from rpicam.utils.state import State

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
        servo = Servo(servo_pin, verbose=True, init_angle=init_angle)
        servo_ops = servo_ops.split(' ')
        servo._logger.info(
            f'Will execute sequence: {servo_ops}{", cycling" if cycle_servo_ops else ""}'
        )
        servo_ops = [ServoOpParser.parse_servo_op(x) for x in servo_ops]

        p = Platform(cam=cam, servos={'s': servo}, verbose=True)
        p.start_recording(**cam_args)
        p.submit_servo_sequence(servo_name='s', sequence=servo_ops, cycle=cycle_servo_ops)
        p.poll_cam_result()
        servo.write_servo_angle(State())

    else:
        cam.record(**cam_args)



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
    '--out',
    type=click.Path(exists=False),
    help='The path to write the output to. If --rotating, this will be a directory, else a file.',
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
@click_option(
    '--rotating',
    is_flag=True,
    help='Whether to repeat this job whenever it ends, storing the resulting files in the output directory. '
    'Oldest files are beginning to be rotated out when storage reaches critical levels.'
)
@click_option(
    '--rotate_fill_perc',
    type=int,
    default=50,
    help='The fill percentage at which oldest files are beginning to be rotated out. Only used when --rotating.'
)
@default_servo_args
def timelapse(out, rotating, rotate_fill_perc, *args, **kwargs):
    from pathlib import Path
    from rpicam.utils.rotating_storage import RotatingStorage

    if rotating:
        outdir = Path(str(out)).stem
        rot = RotatingStorage(outdir, file_ext='.mp4', file_prefix='timelapse', rotate_fill_perc=rotate_fill_perc)
        try:
            for filename in rot:
                _timelapse(outfile=filename, *args, **kwargs)
        except KeyboardInterrupt:
            pass
    else:
        _timelapse(outfile=out, *args, **kwargs)


def main():
    cli()


if __name__ == "__main__":
    main()
