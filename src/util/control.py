'''
this file places the implementation of functions and classes that
feasilate the workflow control of the abacus agent.

Usage
-----
from abacusagent.util.control import FlowEnvironment

def func(a, b):
    return a + b

@mcp.tool()
def workflow_example(x: int, y: int) -> int:

    # initialize the FlowEnvironment
    myenv = FlowEnvironment('workflow_example')
    
    # Example 1: run the first function within the environment
    res = myenv.run(func, a=x, b=y)
    if not myenv.still_alive():
        return myenv.dump() # if the environment is not alive, dump the state
    
    # Example 2: run another function
    res = myenv.run(func, a=res, b=10)
    if not myenv.still_alive():
        return myenv.dump() # if the environment is not alive, dump the state
    
    # ...
    # ...
    # ...
    # after runs...
    return myenv.dump()  # dump the state at the end
'''

import json
import time
import unittest
import logging
from functools import wraps

class FlowEnvironment:
    '''
    a class to represent the state of the workflow.
    '''
    def __init__(self, name: str, flog=None, fstate=None):
        '''
        instantiate the FlowEnvironment with a name and an optional log file.
        
        Parameters
        ----------
        name : str
            The name of the workflow.
        flog : str, optional
            The log file to record the workflow state. If None, no logging is performed.
        '''
        self.name = name
        self.state = {
            'workflow': self.name,
            'start_time': time.strftime("%Y.%m.%d %H:%M:%S"),
            'end_time': None,
            'results': [],
            'flog': flog
        }
        self.fstate = fstate
        self.avail = True
        # initialize the logging if flog is provided
        if flog is not None:
            logging.basicConfig(
                filename=flog, 
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s')
            logging.info(f"Workflow {self.name} initialized at "
                         f"{self.state['start_time']}")
    
    def refresh(self, t=None):
        '''
        refresh the time
        '''
        if self.still_alive():
            self.state['end_time'] = t \
                if t is not None else time.strftime("%Y.%m.%d %H:%M:%S")
            logging.info(f"Workflow {self.name} refreshed at "
                         f"{self.state['end_time']}")
        else:
            logging.warning(f"Workflow {self.name} is not available, "
                            f"cannot refresh the state.")
    
    def kill(self) -> dict:
        '''
        end the workflow and return the state.
        '''
        self.refresh()
        self.avail = False
        logging.info(f"Workflow {self.name} killed at "
                     f"{self.state['end_time']}")
        logging.shutdown()
        return self.state
    
    def still_alive(self):
        '''
        check the status of the workflow.
        Returns True if the workflow is available, False otherwise.
        '''
        logging.info(f"Checking if workflow {self.name} is still alive."
            f": {self.avail}")
        return self.avail
    
    def dump(self):
        '''
        dump the state to a json file.
        if fn is None, dump to a file named by the workflow name.
        '''
        if self.fstate is not None:
            # fn = f'{self.name}-{time.strftime("%Y%m%d-%H%M%S")}.json'
        
            with open(self.fstate, 'w') as f:
                json.dump(self.state, f, indent=4)
        
        return self.state
    
    def run(self, func, *args, **kwargs):
        '''
        run a function and record the state.
        '''
        if not self.still_alive():
            logging.error(f"Workflow {self.name} is not available, "
                          f"cannot run the function.")
            return self.state
        
        # if the environment is still alive
        task_name = func.__name__ if hasattr(func, '__name__') \
            else str(func)
        _t = time.time()
        
        # there are cases that user call this function like
        # env.run(func(1, 2)), what is really passed is the
        # result of the function, not the function itself.
        if not callable(func):
            self.state['results'].append(
                {
                    'task': task_name,
                    'return': func,
                    'args': args,
                    'kwargs': kwargs,
                    'duration': time.time() - _t,
                    'exception': []
                }
            )
            logging.warning(f"Function {task_name} is not callable, "
                           f"returning the result directly.")
            self.refresh()
            return func
        
        # callable case, error catching is needed
        base = {
            'task': task_name,
            'args': args,
            'kwargs': kwargs,
            'duration': None,
            'exception': []
        }
        try:
            result = func(*args, **kwargs)
            self.state['results'].append(
                {
                    **base,
                    'return': result,
                    'duration': time.time() - _t,
                    'exception': []
                }
            )
            logging.info(f"Function {task_name} executed successfully, "
                         f"returning the result.")
            return result
        except Exception as e:
            self.state['results'].append(
                {
                    **base,
                    'return': None,
                    'duration': time.time() - _t,
                    'exception': str(e)
                }
            )
            logging.error(f"Function {task_name} raised an exception: {e}")
            # if an exception occurs, kill the environment
            self.kill()
            return self.state
        finally:
            self.refresh()
            # refresh the end time after the function is executed
    
    # support the decorator protocol
    def decorate(self, func):
        '''
        a decorator to run a function within the environment.
        '''
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.run(func, *args, **kwargs)
        return wrapper
    
    def __call__(self, func):
        '''
        make the FlowEnvironment callable, so that it can be used as a decorator.
        '''
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.run(func, *args, **kwargs)
        return wrapper
    
    def get(self):
        '''
        get the `return` value of the last run function.
        '''
        if not self.state['results']:
            return None
        return self.state['results'][-1].get('return', None)

    def __str__(self):
        myself = '\nABACUS Agent Flow Environment\n'
        myself +=  '-----------------------------\n'
        myself += f'Workflow Name: {self.name}\n'
        myself += f'Start Time: {self.state["start_time"]}\n'
        myself += f'End Time: {self.state["end_time"]}\n'
        myself += f'Still Alive: {self.still_alive()}\n'
        myself += f'Results:\n'
        for res in self.state['results']:
            myself += f'  - Task: {res["task"]}\n'
            myself += f'    Return: {res.get("return", None)}\n'
            myself += f'    Duration: {res["duration"]}\n'
            myself += f'    Exception: {res["exception"]}\n'
            myself += f'    Args: {res["args"]}\n'
            myself += f'    Kwargs: {res["kwargs"]}\n'
        return myself

    def __repr__(self):
        return self.__str__()
    
    # support the context manager protocol
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        '''
        exit of the context manager.
        If an exception occurs, kill the environment.
        If no exception occurs, just refresh the environment.
        '''
        if exc_type is not None:
            self.kill()
        else:
            self.refresh()

class FlowEnvironmentTest(unittest.TestCase):
    '''
    a unittest for the FlowEnvironment class.
    '''
    def setUp(self):
        self.env = FlowEnvironment('test_env')

    def test_init(self):
        self.assertEqual(self.env.name, 'test_env')
        self.assertTrue(self.env.still_alive())
        self.assertIsInstance(self.env.state, dict)
        self.assertIn('workflow', self.env.state)
        self.assertIn('start_time', self.env.state)
        self.assertIn('results', self.env.state)
        
        self.assertEqual(self.env.state['workflow'], 'test_env')
        self.assertIsInstance(self.env.state['start_time'], str)
        self.assertEqual(self.env.state['results'], [])
        
    def test_refresh(self):
        start_time = self.env.state['start_time']
        print('sleep 1 second to refresh the environment...')
        time.sleep(1)
        self.env.refresh()
        self.assertGreater(self.env.state['end_time'], start_time)
        self.assertTrue(self.env.still_alive())
    
    def test_kill(self):
        self.env.kill()
        self.assertFalse(self.env.still_alive())
        self.assertIsNotNone(self.env.state['end_time'])
    
    def test_dump(self):
        state = self.env.dump()
        self.assertIsInstance(state, dict)
        self.assertEqual(state['workflow'], 'test_env')
        self.assertIn('start_time', state)
        self.assertIn('end_time', state)
        self.assertIn('results', state)
        
    def test_run(self):
        def func(a, b):
            return a + b
        result = self.env.run(func, 1, 2)
        self.assertEqual(result, 3)
        self.assertIn('results', self.env.state)
        self.assertEqual(len(self.env.state['results']), 1)
        self.assertEqual(self.env.state['results'][0]['return'], 3)
        self.assertTrue(self.env.still_alive())
        self.assertGreater(self.env.state['results'][0]['duration'], 0)
    
    def test_run_with_args(self):
        def func(a, b):
            return a * b
        result = self.env.run(func, a=3, b=4)
        self.assertEqual(result, 12)
        self.assertIn('results', self.env.state)
        self.assertEqual(len(self.env.state['results']), 1)
        self.assertEqual(self.env.state['results'][0]['return'], 12)
        self.assertTrue(self.env.still_alive())
        self.assertGreater(self.env.state['results'][0]['duration'], 0)
        
    def test_run_with_non_callable(self):
        def func(a, b):
            return a + b
        result = self.env.run(func(1, 2))
        self.assertEqual(result, 3)
        self.assertIn('results', self.env.state)
        self.assertEqual(len(self.env.state['results']), 1)
        self.assertEqual(self.env.state['results'][0]['return'], 3)
        self.assertTrue(self.env.still_alive())
        self.assertGreater(self.env.state['results'][0]['duration'], 0)
    
    def test_run_with_exception(self):
        def func(a, b):
            return a / b
        
        result = self.env.run(func, 1, 0)
        self.assertFalse(self.env.still_alive())
        self.assertIn('exception', self.env.state['results'][-1])
        self.assertIsNotNone(self.env.state['results'][-1]['exception'])
        self.assertIn('division by zero', self.env.state['results'][-1]['exception'])
        self.assertIsInstance(result, dict)
        
    def test_run_again_after_exception(self):
        def func(a, b):
            return a / b
        res = self.env.run(func, 1, 0)
        self.assertFalse(self.env.still_alive())
        
        result = self.env.run(func, 1, 2)
        self.assertFalse(self.env.still_alive())
        self.assertDictEqual(result, res)  # should return the state after exception
        
    def test_context_manager(self):
        def func(a, b):
            return a + b
        
        with FlowEnvironment('context_test') as env:
            result = env.run(func, 1, 2)
            
        self.assertEqual(result, 3)
        self.assertTrue(env.still_alive())
        self.assertIn('results', env.state)
        self.assertEqual(len(env.state['results']), 1)
        self.assertEqual(env.state['results'][0]['return'], 3)
        self.assertGreater(env.state['results'][0]['duration'], 0)
    
    def test_context_manager_exception(self):
        def func(a, b):
            return a / b
        
        with FlowEnvironment('context_test_exception') as env:
            result = env.run(func, 1, 0)
        
        self.assertFalse(env.still_alive())
        self.assertIn('exception', env.state['results'][-1])
        self.assertIsNotNone(env.state['results'][-1]['exception'])
        self.assertIn('division by zero', env.state['results'][-1]['exception'])
        self.assertIsInstance(result, dict)
        
        print(env)
    
    def test_decoractor(self):
        @self.env.decorate
        def add(a, b):
            return a + b
        
        result = add(1, 2)
        self.assertEqual(result, 3)
        self.assertIn('results', self.env.state)
        self.assertEqual(len(self.env.state['results']), 1)
        self.assertEqual(self.env.state['results'][0]['return'], 3)
        self.assertTrue(self.env.still_alive())
        
    def test_decorator_with_exception(self):
        @self.env.decorate
        def divide(a, b):
            return a / b
        
        result = divide(a=1, b=0)
        self.assertFalse(self.env.still_alive())
        self.assertIn('exception', self.env.state['results'][-1])
        self.assertIsNotNone(self.env.state['results'][-1]['exception'])
        self.assertIn('division by zero', self.env.state['results'][-1]['exception'])
        self.assertIsInstance(result, dict)
        self.assertEqual(len(self.env.state['results']), 1)
        self.assertEqual(self.env.state['results'][0]['return'], None)
        print(self.env)
    
if __name__ == '__main__':
    unittest.main(exit=True)

    # example
    
    def add(a, b):
        return a + b
    
    def multiply(a, b):
        return a * b
    
    def divide(a, b):
        return a / b
    
    def myworkflow(x: int, y: int, fstate=None) -> int:
        '''
        an example workflow function.
        '''
        myenv = FlowEnvironment('myworkflow', fstate=fstate)
        
        res = myenv.run(add, a=x, b=y)
        if not myenv.still_alive():
            return myenv.dump()
        
        res = myenv.run(multiply, res, 10)
        if not myenv.still_alive():
            return myenv.dump()
        
        res = myenv.run(divide, res, 0)
        if not myenv.still_alive():
            return myenv.dump()
        
        res = myenv.run(add, res, 100)
        if not myenv.still_alive():
            return myenv.dump()
        
        return myenv.dump()
    
    # run the example workflow
    result = myworkflow(5, 3, fstate='what_the_llm_reads.json')
    print(result)
    