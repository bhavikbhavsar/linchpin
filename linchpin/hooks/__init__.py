"""
example Pinfile for reference::
---
openstack:
  topology: ex_os_server.yml
  layout: openshift-3node-cluster.yml
  hooks:
    postup:              # sub-state is specified
        - name: do_something
          type: shell
          actions:
            - samvaran
        - name: manipulate_inventory
          type: shell
          path: /tmp/shellscripts
          actions:
            - thisisshell.sh
        - name: post_up
          type: ansible
          actions:
            - playbook: test_playbook.yaml
              vars: test_var.yaml
              extra_vars: { 'testvar': 'world'}
    preup:              # sub-state is specified
        - name: do_something
          type: shell
          actions:
            - echo ' this is post up operation Hello hai how r u ?'
        - name: build_openshift_cluster
          type: ansible
          actions:
            - playbook: test_playbook.yaml
              vars: test_var.yaml
              extra_vars: { 'testvar': 'world'}
    postdestroy:
        - name: do_something
          type: shell
          actions:
            - echo ' this is post up operation Hello hai how r u ?'
        - name: postdown_task
          type: ansible
          actions:
            - playbook: test_playbook.yaml
              vars: test_var.yaml
              extra_vars: { 'testvar': 'world'}

"""

import ast
import sys

from linchpin.hooks.action_managers import ACTION_MANAGERS
from linchpin.exceptions import ActionManagerError


class ActionBlockRouter(object):
    """
    Proxy pattern implementation for fetching actionmanagers by name
    """

    def __init__(self, name, *args, **kwargs):

        self.__implementation = self.__get_implementation(name)(name,
                                                                *args,
                                                                **kwargs)

    def __getattr__(self, name):

        return getattr(self.__implementation, name)

    def __get_implementation(self, class_name):
        '''
        Fetches implementation of lcass from linchpin.hooks.action_managers
        :param name: action manager class name
        '''

        action_class = ACTION_MANAGERS.get(class_name, None)
        if action_class is None:
            raise ActionManagerError('Action Class {0}'
                                     'not found '.format(class_name))
        return action_class


class LinchpinHooks(object):

    def __init__(self, api):
        """
        LinchpinHooks class constructor
        :param api: LinchpinAPI object
        """

        self.api = api
        self.api.bind_to_hook_state(self.run_hooks)


    def prepare_ctx_params(self):
        """
        prepares few context parameters based on the current target_data
        that is being set. these parameters are based topology name.
        """

        topology_name = self.api.get_evar("topology_name")

        res_file = '{0}{1}'.format(topology_name,
                                   self.api.get_cfg('extensions', 'resource'))

        res_pthT = self.api.target_data['extra_vars']['default_resources_path']
        res_file = '{0}/{1}'.format(res_pthT, res_file)
        self.api.target_data['extra_vars']['resource_file'] = res_file

        # do this to avoid E113 from flake8
        inv_file_tmp = self.api.get_evar("inventory_file")
        self.api.target_data['extra_vars']['inventory_file'] = inv_file_tmp

        # do this to avoid E113 from flake8
        inv_dir_tmp = self.api.get_evar("inventory_dir")
        self.api.target_data['extra_vars']['inventory_dir'] = inv_dir_tmp


    def run_hooks(self, state, is_global=False):
        """
        Function to run hook all hooks from Pinfile based on the state
        :param state: hook state (currently, preup, postup,
        predestroy, postdestroy)
        :param is_global: whether the hook is global (can be applied to
        multiple targets)
        """

        hooks_data = self.api.target_data.get('hooks', None)

        if hooks_data and str(state) in hooks_data:
            self.api.ctx.log_debug('running {0} hooks'.format(state))

            self.prepare_ctx_params()

            # fetches all the state_data , ie., all the action blocks inside
            # state of the target

            state_data = hooks_data.get(str(state), None)

            # Print out error message if the hooks are not found
            if state_data is None:
                self.api.ctx.log_state('{0} hook not found'
                                       ' in PinFile'.format(state))
                return

            # current target data extravars are fetched
            tgt_data = self.api.target_data.get('extra_vars', None)
            self.run_actions(state_data, tgt_data)


    def run_actions(self, action_blocks, tgt_data, is_global=False):
        """
        Runs actions inside each action block of each target

        :param action_blocks: list of action_blocks each block constitues
                       to a type of hook
        :param tgt_data: data specific to target, which can be dict of
        topology , layout, outputs, inventory
        :param is_global: scope of the hook

        example: action_block:
        - name: do_something
          type: shell
          actions:
            - echo ' this is 'postup' operation Hello hai how r u ?'
        """

        if is_global:
            raise NotImplementedError('Run Hooks is not implemented \
                                       for global scoped hooks')
        else:
            # a_b -> abbr for action_block
            for a_b in action_blocks:
                action_type = a_b['type']
                ab_ctx = a_b['context'] if 'context' in a_b else True
                if 'path' not in a_b:
                    # if the path is not defined it defaults to
                    # workspace/hooks/typeofhook/name
                    a_b['path'] = '{0}/{1}/{2}/{3}/'.format(
                        self.api.ctx.workspace,
                        self.api.get_evar('hooks_folder',
                                          default='hooks'),
                        a_b['type'],
                        a_b['name'])

                if 'action_manager' in a_b:
                    # fetches the action object from the path
                    # add path to python path
                    sys.path.append(a_b['path'])
                    # get the module path
                    module_path = '{0}/{1}'.format(a_b['path'],
                                                   a_b['action_manager'])
                    # get module src
                    module_src = open(module_path, 'r').read()
                    # strip .py ext from module path
                    module_path = module_path.strip('.py')
                    # strip .py ext from action_manager
                    a_b['action_manager'] = a_b['action_manager'].strip('.py')
                    # parse the module
                    module_src = ast.parse(module_src)
                    # get all classes inside the class
                    classes = ([node.name
                               for node in ast.walk(module_src)
                               if isinstance(node, ast.ClassDef)])

                    # choose the first name as the class name
                    class_name = classes[0]
                    # import the module with class name, it should work
                    module = __import__(a_b['action_manager'])
                    # get the class
                    class_ = getattr(module, class_name)
                    # a_b_obj is action_block_object
                    a_b_obj = class_(action_type, a_b, tgt_data, context=ab_ctx)
                else:
                    a_b_obj = ActionBlockRouter(action_type,
                                                a_b,
                                                tgt_data,
                                                context=ab_ctx)
                try:
                    self.api.ctx.log_state('-------\n'
                                           'start hook'
                                           ' {0}:{1}'.format(a_b['type'],
                                                             a_b['name']))

                    # validates the class object
                    a_b_obj.validate()
                    # executes the hook
                    a_b_obj.execute()

                    # intentionally using print here
                    self.api.ctx.log_state('end hook {0}:{1}\n-------'.format(
                                           a_b['type'], a_b['name']))
                except Exception as e:
                    self.api.ctx.log_info(str(e))
