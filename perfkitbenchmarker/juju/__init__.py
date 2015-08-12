# This is a proof-of-concept module to integrate juju into perfkitbenchmarker

from perfkitbenchmarker import flags

import argparse
import sys
import subprocess
import shlex
import yaml
import os.path


# Juju-centric FLAGS
flags.DEFINE_string('workload', '',
                    'Specify a bundle.yaml that represents the workload to run')

def juju():
    """
    This is our main entry point, called when pkb.py fails to parse via gflags
    """

    # ["./pkb.py", "--cloud=amazon", "--workload=foo.yaml", "--benchmarks=cassandra-stress:stress", "--machine_type=cassandra-stress:t1.micro", "--zone=us-east-1b"]
    parser = argparse.ArgumentParser()
    parser.add_argument("--cloud", help="display a square of a given number")
    parser.add_argument("--workload", help="display a square of a given number")
    parser.add_argument("--benchmarks", help="display a square of a given number")
    parser.add_argument("--machine_type", help="display a square of a given number")
    parser.add_argument("--zone", help="display a square of a given number")

    args = parser.parse_args()
    # sys.stdout.write("cloud=%s\nworkload=%s\nbenchmarks=%s\nmachine_type=%s\nzone=%s\n" %(
    # args.cloud, args.workload, args.benchmarks, args.machine_type, args.zone))

    # Assumptions: required tools installed (juju-quickstart, juju) and a configured environments.yaml

    # Verify juju is installed
    # TODO: Verify version is at least 1.24+ for actions
    if juju_version():

        # Verify the cloud name exists in environments.yaml
        environments = get_juju_environments()

        # if we decide to format the cloud parameter as cloud=juju:amazon, then this should work:
        # cloud = args.cloud[5:]

        if args.cloud in environments:
            # Bootstrap, bootstrap?
            if not is_bootstrapped(cloud=args.cloud):
                bootstrap(cloud=args.cloud)

            # TODO: Deploying local bundles needs JUJU_REPOSITORY set
            # juju-quickstart -n bundle-name bundle.yaml || juju deployer -c bundle:mediawiki-single/7
            # TODO: figure out how to overwrite machine_type
            cmd = "juju-deployer -c %s -e %s" % (os.path.expanduser(args.workload), args.cloud)
            run_command(cmd)

            if args.benchmarks:
                # juju action run benchmarks (i.e., cassandra-stress:stress would run juju action run cassandra-stress/0 stress)
                unit = args.benchmarks[:args.benchmarks.index(':')]
                action = args.benchmarks[args.benchmarks.index(':')+1:]
                cmd = "juju action do %s/0 %s" % (unit, action)
                output = run_command(cmd)
                print output
                # parse for UUID
                # Action queued with id: 765ef202-9585-4c03-8be9-de45a2155d50
                ACTION_UUID = output[output.index(':')+2:]

                # juju action fetch --wait 0 ACTION_UUID
                cmd = 'juju action fetch --wait 0 %s' % ACTION_UUID
                output = run_command(cmd)

                # dump `juju action fetch` output to stdout
                sys.stdout.write(output)

            return 0

    return 1


def is_bootstrapped(cloud=None):
    cmd = 'juju status'
    if cloud:
        cmd += " -e %s" % cloud
    try:
        output = run_command(cmd)
    except subprocess.CalledProcessError:
        return False
    return True

def bootstrap(cloud=None):
    cmd = 'juju bootstrap'
    if cloud:
        cmd += " -e %s" % cloud
    output = run_command(cmd)
    return output


def run_command(cmd):
    return subprocess.check_output(shlex.split(cmd))


def get_juju_environments(env=os.path.expanduser('~/.juju/environments.yaml')):
    environments = []

    if os.path.exists(env):
        f = open(env, 'r')
        raw = f.read()
        f.close()

        data = yaml.load(raw)
        for name in data['environments']:
            environments.append(name.strip())

    return environments


def juju_version():

    try:
        output = run_command('juju version')
        return output.strip()
    except:
        pass
    return None
