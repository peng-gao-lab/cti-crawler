import os
import subprocess
import time
from config.root_settings import *
from utils.multithreaded_task_scheduler import MultiThreadedTaskScheduler

in_docker_container = bool(os.environ.get('IN_DOCKER_CONTAINER', False))

if __name__ == "__main__":
    try:
        while 1:
            # This is commented out for now since we aren't using proxy pool right now.
            # if in_docker_container:
            #     # sleep for 90 seconds to wait for proxy pool to load
            #     time.sleep(90)
            crawler_type_file_paths = [CTI_REPORTS_CRAWLERS_DIR, THREAT_ENCYCLOPEDIAS_CRAWLER_DIR]
            module_paths = [CTI_REPORTS_CRAWLERS_MODULE_PATH, THREAT_ENCYCLOPEDIAS_CRAWLERS_MODULE_PATH]
            py_file_lsts = [cti_blogs, threat_encyclopedias]
            cmdline_lst = []

            # Add python commands to cmdline_lst
            for i in range(len(py_file_lsts)):
                crawler_type_file_path = crawler_type_file_paths[i]
                module_path = module_paths[i]
                py_files = py_file_lsts[i]

                for py in py_files:
                    if os.path.exists(f"{crawler_type_file_path}/{py}"):
                        crawler_name = os.path.splitext(py)[0]
                        cmdline = ['python3', '-m', '{}{}'.format(module_path, crawler_name)]
                        cmdline_lst.append(cmdline)
                    else:
                        print(f"py file {py} does not exist")
            
            def main_runner_helper(cmd):
                child = subprocess.Popen(cmd)
                child.communicate()[0]
                return child.returncode
                
            mtts = MultiThreadedTaskScheduler(NUM_THREADS_MAIN_DRIVER_FUNCTION, main_runner_helper, 'Main', \
                        check_num_results=len(cmdline_lst), tasks=cmdline_lst)
            mtts.start()
            mtts.wait()


            print('Computing daily diffs...')
            os.system('python3 -m {}'.format(COMPUTE_DAILY_DIFFS_FILE_PATH))
            print('Finished computing daily diffs')
            
            print("Done!")
            if LOOP_TIME == -1:
                break
            
            print('Now sleeping for 24 hours')

            time.sleep(LOOP_TIME)
    
    except Exception as e:
        print(e)
        print("Error: unable to start thread")
