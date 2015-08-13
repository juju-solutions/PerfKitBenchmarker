
import jujuclient
import deployer
import yaml


class Juju(jujuclient.Environment):
  def deployer(bundle):
    # make this not use cmdline

  def action_do(service, action, parameters=None):
    # api this up a bitt yeahhhh

  def action_wait(uuid):
    # waity wait

  def benchmark(service, action, parameters=None):
    # uuid = self.action_do(*args, *kwargs)
    # results = self.action_wait(uuid)
    return results


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


def Main(bundle, constraints=None):
  pass
