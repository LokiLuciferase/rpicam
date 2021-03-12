"""Console script for rpicam."""
import sys
import click


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
def cli(args=None):
    pass


@cli.command('live', short_help='Display a live video stream.')
@click.option('-s', '--spf', type=float, default=0.5, help='Seconds per frame.')
def live(spf):
    from rpicam.cams import LivePreviewCam
    try:
        lpc = LivePreviewCam()
        lpc.record(spf=spf)
    except KeyboardInterrupt:
        pass


@cli.command('timelapse', short_help='Create a timelapse video.')
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
def timelapse(duration, spf, fps, resolution, outfile):
    from datetime import timedelta
    from rpicam.cams import TimelapseCam, AnnotateFrameWithDt

    tc = TimelapseCam(
        callbacks=[AnnotateFrameWithDt()],
        verbose=True,
        camera_rotation=0,
        resolution=resolution,
    )
    tc.record(
        fps=fps,
        duration=timedelta(minutes=duration),
        sec_per_frame=spf,
        outfile=outfile,
    )


@cli.command('servo', short_help='Move a servo using pre-defined commands.')
@click.option('-p', '--pin', type=int, help='The BOARD pin connected to the servo.')
@click.option('-c', '--cycle', is_flag=True, help='Whether to cycle the given command sequence.')
@click.argument(
    'ops', type=click.Choice(['pause', 'cw', 'ccw', 'noon', 'full_ccw', 'full_cw']), nargs=-1
)
def servo(ops, pin, cycle):
    from rpicam.servo import Servo, pause, full_ccw, full_cw, cw, ccw

    ops_map = {'pause': pause, 'full_cw': full_cw, 'full_ccw': full_ccw, 'cw': cw, 'ccw': ccw}
    ops = [ops_map[x] for x in ops if x in ops_map]
    s = Servo(pin, verbose=True)
    s.execute_sequence(ops, cycle=cycle)


def main():
    cli()


if __name__ == "__main__":
    main()
