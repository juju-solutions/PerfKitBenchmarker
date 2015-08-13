# This is a proof-of-concept module to integrate juju into perfkitbenchmarker

import os
import sys
import yaml
import argparse
import deployer
import logging
import jujuclient
import subprocess

from perfkitbenchmarker import flags


# Juju-centric FLAGS
flags.DEFINE_string('workload', '',
                    'Specify a bundle.yaml that represents the workload to run')


class DeploymentError(Exception):
  pass


class BenchmarkError(Exception):
  pass


class Juju(jujuclient.Environment):
  @classmethod
  def bootstrap(cls, env):
    pass

  #@classmethod
  #def installed(cls):
  #  try:
  #    cls()
  #    cls.cmd(['is'])
  #  except OSError:
  #    return False

  #  return True

  def deployer(self, bundle):
    try:
      out = self.cmd(['deployer', '-c', os.path.expanduser(bundle)])
    except IOError as e:
      logging.exception('Bundle deployment failed')
      raise DeploymentError()
    except OSError:
      logging.exception('Deployer not installed')
      raise

    return

  def is_action(self, service, action):
    search = self.actions.service_actions(service)
    action_specs = search['results'][0].get('actions', None)

    if not action_specs:
      return False

    return action in action_specs['ActionSpecs'].keys()


  def action_do(self, unit, action, parameters=None):
    out = self.actions.enqueue_units(unit, action, parameters)
    results = out.get('results')[0] # We're only doing one unit at a time

    if 'error' in results:
      raise BenchmarkError('Failed to run benchmark: %s' %
                           results['error']['Message'])

    return results['action']['tag']

  def action_info(self, tag):
    return self.actions.info([{'Tag': tag}])['results'][0]

  def action_wait(self, uuid):
    # Use the allwatcher API?
    data = {}
    while True: # Permission to kill me for doing this
      result = self.action_info(uuid)
      if result['status'] in ('failed', 'completed', 'cancelled'):
        data['started'] = result['started']
        data['completed'] = result['completed']
        data['output'] = result.get('output', None)
        break

    return data

  def benchmark(self, service, action, parameters=None):
    if service not in self.status()['Services']:
      raise DeploymentError('%s is not actually deployed' % service)

    # Get the first unit FOR NOW, work on multiples
    unit = self.units(service)[0]
    if not self.is_action(service, action):
      raise BenchmarkError('%s is not a valid benchmark for %s' % (action,
                                                                   service))
    action_tag = self.action_do(unit, action)
    return self.action_wait(action_tag)

  def units(self, service=None):
    if service:
      return [u for u in self.status()['Services'][service]['Units'].keys()]

    units = []
    for service in self.services():
      units = units + self.units(service)

    return units

  def services(self):
    return [s for s in self.status()['Services'].keys()]

  def cmd(self, args, env=None):
    if not env:
      env = {}

    popen_env = os.environ.copy()
    # Always override this
    env['JUJU_ENV'] = self.name
    env['JUJU_HOME'] = env.get('JUJU_HOME', os.path.expanduser('~/.juju'))

    popen_env.update(env)

    cmd = ['juju'] + args
    logging.debug('Running: %s', ' '.join(cmd))

    try:
      p = subprocess.Popen(cmd, env=popen_env, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    except OSError as e:
      if e.errno != errno.ENOENT:
        raise
      raise OSError("juju not found, do you have Juju installed?")
    out, err = p.communicate()
    if p.returncode:
      raise IOError("juju command failed {!r}:\n"
                    "{}".format(args, err.decode('utf-8', 'replace')))
    return out.decode("utf-8", "replace") if out else None


def BuildBundle(bundle, overrides=None):
  if 'services' not in bundle:
    raise Exception('Not a valid bundle')

  service_list = bundle['services'].keys()
  for service in service_list:
    if '_GLOBAL' in overrides:
      bundle['services'][service]['constraints'] = overrides['_GLOBAL']

    if service in overrides:
      bundle['services'][service]['constraints'] = overrides[service]

  return bundle


def Main(argv=sys.argv):
  parser = argparse.ArgumentParser()
  parser.add_argument("--cloud", help="The juju environment to use")
  parser.add_argument("--workload", help="A bundle file defining the workload to deploy")
  parser.add_argument("--benchmarks", help="The benchmark to run, i.e., mycharm:myaction")
  parser.add_argument("--machine_type", help="The machine_type to run, if different than the bundle, specified by charm, i.e., mycharm:t1-micro")
  parser.add_argument("--zone", help="The zone to deploy to")

  args = parser.parse_args(argv[1:])

  try:
    juju = Juju.connect(args.cloud)
  except jujuclient.EnvironmentNotBootstrapped as e:
    logging.error('%s is not bootstrapped or defined', args.cloud)
    return 1

  if not args.benchmarks:
    logging.error('No benchmark defined')
    return 1

  juju.deployer(args.workload)
  service, action = args.benchmarks.split(':')
  results = juju.benchmark(service, action)

  sys.stdout.write(yaml.dump(results, default_flow_style=False))
  return 1 if results['status'] != 'completed' else 0
  #if not Juju.installed():
  #  logging.error('Juju 1.24.4 or greater needs to be installed')
  #  return 1
