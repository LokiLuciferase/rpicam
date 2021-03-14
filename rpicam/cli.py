"""Console script for rpicam."""
import sys
import click


@click.group(short_help='Servo controls.', context_settings=dict(help_option_names=["-h", "--help"]))
def servo(args=None):
    pass


@click.group(short_help='Recording functions.', context_settings=dict(help_option_names=["-h", "--help"]))
def cam(args=None):
    pass


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
def cli(args=None):
    pass


cli.add_command(cam)
cli.add_command(servo)


@servo.command('move', short_help='Move a servo using pre-defined commands.')
@click.option('-p', '--pin', type=int, default=7, help='The BOARD pin connected to the servo.')
@click.option('-c', '--cycle', is_flag=True, help='Whether to cycle the given command sequence.')
@click.argument(
    'ops', type=str, nargs=-1
)
def move(ops, pin, cycle):
    from rpicam.servo import Servo, parse_servo_op

    ops = [parse_servo_op(x) for x in ops]
    s = Servo(pin, verbose=True)
    s.execute_sequence(ops, cycle=cycle)


@cam.command('live', short_help='Display a live video stream.')
@click.option('-s', '--spf', type=float, default=0.5, help='Seconds per frame.')
def live(spf):
    from rpicam.cams import LivePreviewCam
    try:
        lpc = LivePreviewCam()
        lpc.record(spf=spf)
    except KeyboardInterrupt:
        pass


@cam.command('timelapse', short_help='Create a timelapse video.')
@click.option(
    '-d', '--duration', type=int, default=120, help='The total recording duration in min.'
)
@click.option('-s', '--spf', type=int, default=10, help='The time between frames in seconds.')
@click.option(
    '-f', '--fps', type=int, default=30, help='The number of frames per second in the final video.'
)
@click.option(
    '-r',
    '--resolution',
    type=int,
    nargs=2,
    help='The resolution of the video (width, height) in px.',
)
@click.option(
    '-o',
    '--outfile',
    type=click.Path(dir_okay=False, exists=False),
    help='The path to write the output file to.',
)
@click.option(
    '--servo_ops',
    type=str,
    default=None,
    help='A space-delimited string of servo operations to perform during timelapse recording. Optional.'
)
@click.option(
    '--servo_pin',
    type=int,
    default=7,
    help='The pin on which the servo is connected. Only required if servo_ops are supplied.'
)
@click.option(
    '--cycle_servo_ops',
    is_flag=True,
    help='Whether to cycle the given servo operations during timelapse recording.'
)
def timelapse(duration, spf, fps, resolution, outfile, servo_ops, servo_pin, cycle_servo_ops):
    from datetime import timedelta
    from rpicam.cams import TimelapseCam, AnnotateFrameWithDt
    from rpicam.platform import Platform
    from rpicam.servo import Servo
    from rpicam.servo import parse_servo_op

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
        servo._logger.info(f'Will execute sequence: {servo_ops}{", cycling" if cycle_servo_ops else ""}')
        servo_ops = [parse_servo_op(x) for x in servo_ops]

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
