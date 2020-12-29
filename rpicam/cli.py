"""Console script for rpicam."""
import sys
import click


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
def cli(args=None):
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
    from rpicam.timelapse import TimelapseCam, AnnotateFrameWithDt

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


def main():
    cli()


if __name__ == "__main__":
    main()
