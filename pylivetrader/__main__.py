#
# Copyright 2015 Quantopian, Inc.
# Modifications Copyright 2018 Alpaca
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from pathlib import Path
import os
import click

from pylivetrader.misc import configloader
from pylivetrader.misc.api_context import LiveTraderAPI
from pylivetrader.algorithm import Algorithm
from pylivetrader.loader import (
    get_algomodule_by_path,
    get_api_functions,
)
from pylivetrader.shell import start_shell


@click.group()
def main():
    from logbook import StreamHandler
    import sys
    StreamHandler(sys.stdout).push_application()


def algo_parameters(f):
    opts = [
        click.option(
            '-f', '--file',
            default=None,
            type=click.Path(
                exists=True, file_okay=True, dir_okay=False,
                readable=True, resolve_path=True),
            help='Path to the file taht contains algorithm to run.'),
        click.option(
            '-b', '--backend',
            default='alpaca',
            show_default=True,
            help='Broker backend to run algorithm with.'),
        click.option(
            '--backend-config',
            type=click.Path(
                exists=True, file_okay=True, dir_okay=False,
                readable=True, resolve_path=True),
            default=None,
            help='Path to broker backend config file.'),
        click.option(
            '--data-frequency',
            type=click.Choice({'daily', 'minute'}),
            default='minute',
            show_default=True,
            help='The data frequency of the live trade.'),
        click.option(
            '-s', '--statefile',
            default=None,
            type=click.Path(writable=True),
            help='Path to the state file. Defaults to <algofile>-state.pkl.'),
        click.argument('algofile', nargs=-1),
    ]
    for opt in opts:
        f = opt(f)
    return f


def process_algo_params(
        ctx,
        file,
        algofile,
        backend,
        backend_config,
        data_frequency,
        statefile):
    if len(algofile) > 0:
        algofile = algofile[0]
    elif file:
        algofile = file
    else:
        algofile = None

    if algofile is None or algofile == '':
        ctx.fail("must specify algo file with '-f' ")

    if not (Path(algofile).exists() and Path(algofile).is_file()):
        ctx.fail("couldn't find algofile '{}'".format(algofile))

    algomodule = get_algomodule_by_path(algofile)
    functions = get_api_functions(algomodule)

    backend_options = None
    if backend_config is not None:
        backend_options = configloader.load_config(backend_config)

    algorithm = Algorithm(
        backend=backend,
        backend_options=backend_options,
        data_frequency=data_frequency,
        algoname=extract_filename(algofile),
        statefile=statefile,
        **functions,
    )
    ctx.algorithm = algorithm
    ctx.algomodule = algomodule
    return ctx


@click.command()
@algo_parameters
@click.pass_context
def run(ctx, **kwargs):
    ctx = process_algo_params(ctx, **kwargs)
    algorithm = ctx.algorithm
    with LiveTraderAPI(algorithm):
        algorithm.run()


@click.command()
@algo_parameters
@click.pass_context
def shell(ctx, **kwargs):
    ctx = process_algo_params(ctx, **kwargs)
    algorithm = ctx.algorithm
    algomodule = ctx.algomodule

    with LiveTraderAPI(algorithm):
        start_shell(algorithm, algomodule)


@click.command()
def version():
    from ._version import VERSION
    click.echo('v{}'.format(VERSION))


def extract_filename(algofile):
    algofilename = algofile
    algofilename = os.path.basename(algofilename)
    if '.py' in algofilename:
        algofilename = algofilename[:-3]
    return algofilename


main.add_command(run)
main.add_command(shell)
main.add_command(version)


if __name__ == '__main__':
    main()
