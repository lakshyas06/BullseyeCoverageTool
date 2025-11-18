######3generate individual covbr for all tests#######
COVBR_ON = False
source_code_directory = 'ip_display\\display13\\Display\\src'
covbrResults_folderName_in_setupDir = "covbrResults"
#####################################################
#TODO: make dataframe to perform one write at end of the thread along with one zero coverage covbr too at the end

#!/usr/bin/env python3
import argparse
import glob
import os
import shutil
import sys

import numpy as np
import time
import multiprocessing
import json
import datetime
import random
from random import randint
from ctypes import c_wchar_p
import logging
from datetime import date

import subprocess
from multiprocessing import active_children
import psutil

import signal
import datetime
import re
import pandas as pd
#formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
def setup_logger(name, log_file, level=logging.INFO):
    handler = logging.FileHandler(log_file)        
    #handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger
projectName = "other"
#file loggers
log_Start_End_of_tests = setup_logger('Start_End_of_tests', 'Start_End_of_tests.csv')
Failing_tests_list = setup_logger('Failing_tests', 'Failing_tests.txt')
Passing_tests_list = setup_logger('Passing_tests', 'Passing_tests.txt')
log_Passing_tests = setup_logger('Passing_tests_log', 'Passing_tests.log')
Exception_tests_list = setup_logger('Exception_tests', 'Exception_tests.txt')
Timeout_tests_list = setup_logger('Timeout_tests', 'Timeout_tests.txt')
log_Exceptions= setup_logger('Exceptions', 'Exceptions.log')
    
def run_covbr(src, dst, new_extension, covfile):
    dst_file = os.path.basename(src) + new_extension  
    dst_file = os.path.join(dst, dst_file)
    if new_extension == ".csv":
        covbr_option = "--csv"
    else:
        covbr_option = ""
    os.system(f'covbr --file {covfile} {src} {covbr_option} > {dst_file}')  
    #print(f'covbr --file {covfile} {src} {covbr_option} > {dst_file}') 
    #shutil.copy(src, os.path.join(dst, dst_file))

def create_covbr_files_recursively(source_code_directory, test_covbr_directory, covfile_path):
    for root, dirs, files in os.walk(source_code_directory):
        relative_path = os.path.relpath(root, source_code_directory)
        new_dir = os.path.join(test_covbr_directory, relative_path)
        os.makedirs(new_dir, exist_ok=True)
        for file in files:
            if file.endswith('.cpp') or file.endswith('.h'):
                run_covbr(os.path.join(root, file), new_dir, '.csv', covfile_path)
   
def accumulate_then_reinitialize_covfile(destCov):
    setupDir = os.path.dirname(os.path.dirname(destCov))
    destCov_new = setupDir + "\\CoverageToBeMergedDir\\"+os.path.basename(destCov)
    destCov_merged = destCov_new.replace(".cov", "_merged.cov")
    destCov_zero = setupDir + "\\GoldenCoverage\\test.cov"

    if os.path.exists(destCov_merged):   
        shutil.copy2(destCov, destCov_new)
        os.system('covmerge.exe -c -f ' + destCov_merged + ' ' + destCov_merged + ' ' + destCov_new)
        os.system(f'del {destCov_new}')
        #log_Exception_tests.info(f'shutil.copy2({destCov}, {destCov_new})')
        #log_Exception_tests.info('covmerge.exe -c -f ' + destCov_merged + ' ' + destCov_merged + ' ' + destCov_new)
        #log_Exception_tests.info(f'del {destCov_new}')
    else:
       raise Exception(f"did not find the destCov_merged file : {destCov_merged}") 
     
    shutil.copy2(destCov_zero, destCov)
    #print(f'shutil.copy2({destCov_zero}, {destCov})')
              
def merge_csv_files(csv1_path, csv2_path, column_name):
    # Read both CSV files into pandas DataFrames
    df_merged = pd.read_csv(csv1_path)
    
    # Check if B.csv exists
    if os.path.exists(csv2_path):
        df2 = pd.read_csv(csv2_path)

        # Ensure both DataFrames have the same number of rows
        if len(df_merged) != len(df2):
            print("Error: Both CSV files must have the same number of rows.")
            return

        # Add the 5th column of df2 to df_merged
        df_merged[column_name] = df2.iloc[:, 4]

        # Delete the second CSV file
        os.remove(csv2_path)
    else:
        # Add an empty column to df_merged
        df_merged['column_name'] = None

    # Save the modified DataFrame back to A.csv
    df_merged.to_csv(csv1_path, index=False)
       
        
def merge_covbr_files(merged_covbr_directory, test_covbr_directory):
    # Iterate over files in merged_covbr_directory
    column_name = os.path.basename(test_covbr_directory)
    for file_name in os.listdir(merged_covbr_directory):
        csv1_path = os.path.join(merged_covbr_directory, file_name)
        csv2_path = os.path.join(test_covbr_directory, file_name)
        merge_csv_files(csv1_path, csv2_path, column_name)
    try:
        os.rmdir(test_covbr_directory)
    except Exception as e:
        return
        

def run_covbr_for_this(destCov, covbr_outDirectory_name,setupDir,device,softwarePath):
    global covbrResults_folderName_in_setupDir, source_code_directory
    source_code_directory = softwarePath.split("package")[0] + source_code_directory
    covbrResults_folder_in_setupDir = f'{setupDir}\\{covbrResults_folderName_in_setupDir+device}\\'
    covbr_directory = covbrResults_folder_in_setupDir+os.path.basename(source_code_directory)
    covbr_outDirectory = covbr_directory+"\\"+covbr_outDirectory_name
    os.system(f'rm -rf {covbr_outDirectory}')
    os.system(f'mkdir {covbr_outDirectory}')
    create_covbr_files_recursively(source_code_directory, covbr_outDirectory, destCov)
    return covbr_directory
    
def run_covbr_for_this_tests(destCov, cwd_containing_test_name,setupDir,device,softwarePath):      
    covbr_outDirectory_name = os.path.basename(cwd_containing_test_name)
    covbr_directory = run_covbr_for_this(destCov, covbr_outDirectory_name,setupDir,device,softwarePath)
    
    covbr_outDirectory = covbr_directory+"\\"+covbr_outDirectory_name
    covFile_name = os.path.basename(destCov)
    merged_covbr_directory_name = covFile_name.replace("_test.cov", "_merged")
    merged_covbr_directory = covbr_directory+"\\"+ merged_covbr_directory_name
    merge_covbr_files(merged_covbr_directory,covbr_outDirectory)

             
def create_folder_copies(base_folder, num_copies):
    for i in range(1, num_copies + 1):
        new_folder = f"Copy{i}_merged"
        new_folder_path = os.path.join(os.path.dirname(base_folder), new_folder)
        if (os.path.exists(new_folder_path)):
            os.system(f'rm -rf {new_folder_path}')
        shutil.copytree(base_folder, new_folder_path)

def create_zerocoverage_covbr_and_its_copies(destCov_zero, noOfWrkProcs,setupDir,device,softwarePath):
    covbr_directory = run_covbr_for_this(destCov_zero, "zero_coverage_covbr",setupDir,device,softwarePath)
    create_folder_copies(covbr_directory+"\\zero_coverage_covbr",noOfWrkProcs)
 
def run_one_unit_process(managedTestList, one_test, covFile, covFileDictionary, config,passingTestlist,device=""):
    try:
        if(one_test in managedTestList):
            try:
                managedTestList.remove(one_test)
            except Exception as e:
                #cpID = str(os.getpid())
                #print(f"{cpID}:!!!!!!!!!!!!!!!!!!!!!!!!EXCEPTION_HANDLING_FAILED OCCURED!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" + str(e))       
                #log_Exceptions.info(f"\n---EXCEPTION_HANDLING_FAILED {cpID}:run_one_unit_process---\n" + str(e))              
                return
            covFileDictionary[covFile] = True
            cpID = str(os.getpid()) # Child process ID
            setupDir = os.getcwd()
            BullseyeDir = os.path.dirname(setupDir)
            thread_file_prefix = covFile.split("_")[0]
            log_Start_End_of_tests.info(f"{cpID},{covFile},start,{one_test}")
                      
            #print("---Child Process--- PID: " + cpID + " started executing!!")
            print(f"{cpID}:---Child Process started executing: {one_test}---")
            ############################################# Config ###########################################################
            try:
                
                localP4VTestPath = str(config["testsPath"])
                path_files = BullseyeDir + "\\path_files\\"
                test = one_test.split("/")[2]
                test_dir = one_test.split("/")[0].split("\"")[1]
                
                configopt = one_test.split("#")[1].split("@")[0]
                workingDir_actualName = setupDir + "\\WorkingDirs\\" + test_dir + "_" + test+ "_" + configopt.strip('\'')
                #softwarePath = setupDir + "\\__Software\\"+thread_file_prefix+"\\"
                softwarePath = str(config["softwarePath"])
                axeFileResolverPath = BullseyeDir + "\\__AxeFileResolver\\"+thread_file_prefix+"\\"
                projectName = str(config["projectName"])
                grits_option = config[projectName+device]["grits_opts"]
                #print(grits_option)
                fulsim_option = config[projectName+device]["fulsim_opts"]
                #print(fulsim_option)
                device_option = config[projectName+device]["device_opts"]
                #print(device_option)
                fblockTestbenchPath = softwarePath+"FblockUvmTestBench.exe"


                working_directory_for_failed_tests_not_required = random.choices([False, True], weights=[config["retainProbability_working_directory_for_failed_tests"], 1-config["retainProbability_working_directory_for_failed_tests"]])[0]
                working_directory_for_passed_tests_not_required = random.choices([False, True], weights=[config["retainProbability_working_directory_for_passed_tests"], 1-config["retainProbability_working_directory_for_passed_tests"]])[0]

            except Exception as e:
                print(f"{cpID}:!!!!!!!!!!!!!!!!!!!!!!!!CONFIG EXCEPTION OCCURED!!!!!!!!!!!!!!!" + str(e))
                log_Exceptions.info(f"\n---CONFIG_EXCEPTION_PID {cpID}:run_one_unit_process---\n" + str(e)) 
                log_Start_End_of_tests.error(f"{cpID},{covFile},CONFIG_EXCEPTION_PID,{one_test}")
                Exception_tests_list.info(one_test)  
                covFileDictionary[covFile] = False                
                return
            
            ################################################################################################################
            
            try:  
                FirstCopyOfworkingDir = setupDir + "\\WorkingDirs\\workingDir_Copy0"
                workingDir = setupDir + "\\WorkingDirs\\workingDir_"+thread_file_prefix 
                if (os.path.exists(workingDir_actualName)):
                    os.system(f'RD /S/Q {workingDir_actualName}')               
                if (os.path.exists(workingDir)):
                    os.rename(workingDir,workingDir_actualName)
                else:
                    shutil.copytree(FirstCopyOfworkingDir, workingDir_actualName)
                os.chdir(workingDir_actualName)
                destCov = (setupDir + "\\GoldenCoverageWorkingDir\\" + covFile)
                os.environ['COVFILE'] = destCov
                file_object=None
                file_object = open(destCov, 'a', 8)    
            except Exception as e:
                os.chdir(setupDir)
                print(f"{cpID}:!!!!!!!!!!!!!!!!!!!!!!!!SETUP EXCEPTION OCCURED!!!!!!!!!!!!!!!" + str(e))                  
                log_Exceptions.info(f"\n---SETUP_EXCEPTION_PID {cpID}:run_one_unit_process---\n" + str(e)) 
                log_Start_End_of_tests.error(f"{cpID},{covFile},SETUP_EXCEPTION_PID,{one_test}")
                Exception_tests_list.info(one_test)  
                covFileDictionary[covFile] = False 
                #managedTestList.append(one_test)                
                return
            finally:
                if file_object:
                    file_object.close()
            ################################################################ RUN TEST ###################################################################
            try:
                ##################################### COPY TEST TO WORKINGDIR #####################################
                try:
                    unit = one_test.split("/")[0]
                    test = one_test.split("/")[2]
                    unit = unit.replace('"', '')
                    unitsBasicDirectory = localP4VTestPath + unit + "\\basic\\"
                    unitsGoldDirectory  = localP4VTestPath + unit + "\\gold\\"
                    testBasicPath = unitsBasicDirectory + test + '\\'
                    testGoldPath = unitsGoldDirectory + test + '\\'
                    gold_folder_name = '__' + projectName +'.-.--'
                    if (gold_folder_name == "__XE3P_V2.-.--"):
                        device_name = re.search(r"/(.*?)(?=\.)",device_option).group(1)
                        #device_name = "xe3pLPG"
                        gold_folder_name = f'__{device_name}.-.--'
                    elif(gold_folder_name == "__XE4_V2.-.--"):
                        gold_folder_name = f'__xe4lpg.-.--'

                    thisTestGoldPath = testGoldPath + gold_folder_name
                    gold_folder_path = os.path.join(workingDir_actualName, "gold")
                    cpPassLogs = ""  # child process pass logs
                    cpFailLogs = ""  # child process fail logs
                    
                    os.chdir(workingDir_actualName)
                    # Deleting previous thread files except DISP tools files
                    subdirs = [x[0] for x in os.walk(workingDir_actualName)]
                    for subdir in subdirs[1:]:
                        if "DISP_tools" not in subdir:
                            shutil.rmtree(subdir)
                        
                    read_files = glob.glob("*.*")
                    for f in read_files:
                        if "path.txt" not in f and ".xml" not in f:
                            os.remove(f)

                    if not os.path.isdir(testBasicPath):
                        os.chdir('..')
                        os.rename(workingDir_actualName,workingDir)
                        raise Exception("Sorry, this tests dosent exists in the local Repo")

                    #os.system('copy ' + testBasicPath + '\\* ' + workingDir_actualName)
                    #os.system('copy ' + testBasicPath+"\\"+test + '.gsf ' + workingDir_actualName)
                    #os.system('copy ' + testBasicPath+"\\"+test + '.cfg ' + workingDir_actualName)
                    #os.system('copy ' + testBasicPath+"\\"+test + '.meta.yaml ' + workingDir_actualName)

                    try:
                        shutil.copytree(testBasicPath, workingDir_actualName, dirs_exist_ok=True)
                        print(f"Directory '{testBasicPath}' copied to '{workingDir_actualName}' (overwriting if necessary).")
                        shutil.copytree(thisTestGoldPath, gold_folder_path, dirs_exist_ok=True)
                        print(f"Directory '{thisTestGoldPath}' copied to '{gold_folder_path}' (overwriting if necessary).")
                    except shutil.Error as e:
                        print(f"Error during copytree: {e}")

                except Exception as e:
                    os.chdir(setupDir)
                    print(f"{cpID}:!!!!!!!!!!!!!!!!!!!!!!!!TESTCOPY EXCEPTION OCCURED!!!!!!!!!!!!!!!" + str(e))
                    log_Exceptions.info(f"\n---TESTCOPY_EXCEPTION_PID {cpID}:run_one_unit_process---\n{unit}\\{test}\n" + str(e)) 
                    log_Start_End_of_tests.error(f"{cpID},{covFile},TESTCOPY_EXCEPTION_PID,{one_test}")
                    Exception_tests_list.info(one_test)  
                    covFileDictionary[covFile] = False                
                    return

                ###################################################################################################
                #runTestLog = workingDir_actualName + "\\" + test + '_ExecLog.log'
                #######################################################################################################################
                try:
                    print(f"{cpID}:Count of tests in queue = {len(managedTestList)}")
                    print(f"{cpID}:RUNNING PipeUVM Testbench")
                    os.chdir(axeFileResolverPath)
                    print("CURRENT DIRECTORY : " + str(os.getcwd()))

                    #os.system('mkdir ' + workingDir_actualName + "\\" + test + "_FD2D")
                    #runTestCmd = 'perl runtest7.pl -testname ' + test + ' -unit ' + unit + '/basic/' + test + ' -config ' + configopt + ' ' +\
                     #            '-grits_opt=\"' + grits_option + '\" ' + '-fulsim_opt=\"' + fulsim_option + '\" ' + \
                     #            '-device=\"' + device_option + '\" ' + ' -bindir ' + axeFileResolverPath + ' -exedir ' + \
                      #           softwarePath + ' -covfile ' + destCov + ' -testdir ' + workingDir_actualName + ' -golddir gold -nogold -nopost -resultroot ' + \
                       #          workingDir_actualName + ' > ' + runTestLog
                    #' -config ' + projectName + 'Test '

                ##################################################################### PIPE UVM EXECUTION ##############################################################################
                    runTestCmd = fblockTestbenchPath + " -tname " + test + " -tdir " + workingDir_actualName + " -ftype display -dunit full_pipe" + " -fulsim_release_path " + softwarePath + " -device" + device_option +" -bdsm_base bc000000 -flatccsbase 84000b7600001 -dcalllog enable"

                    print("COMMAND : " + runTestCmd)
                    testStartTime = time.time()

                    try:
                        process = subprocess.Popen(runTestCmd)
                        process.wait(timeout=6000)
                        if COVBR_ON:
                            try:                            
                                run_covbr_for_this_tests(destCov, workingDir_actualName,setupDir,device,softwarePath)
                                accumulate_then_reinitialize_covfile(destCov)
                            except Exception as e:
                                print(f"{cpID}:!!!!!!!!!!!!!!!!!!!!!!!!COVBR EXCEPTION OCCURED!!!!!!!!!!!!!!!" + str(e))
                                log_Exceptions.info(f"\n---COVBR_EXCEPTION_PID {cpID}:run_one_unit_process---\n" + str(e))               
                        covFileDictionary[covFile] = False
                    except Exception as e:
                        covFileDictionary[covFile] = False
                        print(f"{cpID}:!!!!!!!!!!!!!!!!!!!!!!!!TIMEOUT EXCEPTION OCCURED!!!!!!!!!!!!!!!" + str(e))
                        current_process = psutil.Process(process.pid)
                        progeny_processes = current_process.children(recursive=True)
                        for progeny in progeny_processes:
                            os.kill(progeny.pid, signal.SIGINT)
                        process.terminate()
                        os.chdir(setupDir)           
                        log_Exceptions.info(f"\n---TIMEOUT_EXCEPTION_PID {cpID}:run_one_unit_process---\n{unit}\\{test}\n" + str(e)) 
                        log_Start_End_of_tests.error(f"{cpID},{covFile},TIMEOUT_EXCEPTION_PID,{one_test}")
                        Timeout_tests_list.info(one_test) 
                        #covFileDictionary[covFile] = False
                        return
                        
                    #os.system(runTestCmd)
                    testEndTime = time.time()
                    testDuration = testEndTime - testStartTime
                    testDuration_str = time.strftime("%H hr %M min %S sec", time.gmtime(testDuration))
                    print(f"{cpID}:TEST TIME : {testDuration_str}")
                    print(f"{cpID}:FINSIHED TB EXECUTION")
                    os.chdir(setupDir)
                    ###################################### CHECK TEST STATUS ##############################################
                    parse_result(test, workingDir_actualName)
                    fd2dDir = workingDir_actualName + "\\fd2d"
                    #if ((os.path.isfile(testGoldPathTkn) == False) or (os.path.isdir(fd2dDir) and len(os.listdir(fd2dDir)) > 0)):
                    if ((os.path.isdir(thisTestGoldPath) and len(os.listdir(thisTestGoldPath)) > 0) and not (os.path.isdir(fd2dDir) and len(os.listdir(fd2dDir)) > 0)):
                        if (working_directory_for_failed_tests_not_required):                       
                            try:
                                os.rename(workingDir_actualName,workingDir)
                            except Exception as e:
                                print("!!!!!!!!!!!!!!!!!!!!!!!!WD_RENAME_BACK EXCEPTION OCCURED!!!!!!!!!!!!!!!" + str(e))
                                log_Exceptions.info(f"\n---WD_RENAME_BACK_EXCEPTION_PID {cpID}:run_one_unit_process---\n{unit}\\{test}\n" + str(e)) 
                                try:
                                    shutil.rmtree(workingDir_actualName)
                                except Exception as e:
                                    log_Exceptions.info(f"\n---WD_RMTREE_EXCEPTION_PID {cpID}:run_one_unit_process---\n{unit}\\{test}\n" + str(e)) 
                                    log_Start_End_of_tests.error(f"{cpID},{covFile},WD_RMTREE_EXCEPTION_PID,{one_test}")   
                                    Exception_tests_list.info(one_test)   
                                log_Start_End_of_tests.error(f"{cpID},{covFile},WD_RENAME_BACK_EXCEPTION_PID,{one_test}")   
                                Failing_tests_list.info(one_test)
                        log_Start_End_of_tests.warning(f"{cpID},{covFile},end,{one_test}")
                        Failing_tests_list.info(one_test)   
                    else:  
                        if (working_directory_for_passed_tests_not_required):
                            try:
                                os.rename(workingDir_actualName,workingDir)
                            except Exception as e:
                                print("!!!!!!!!!!!!!!!!!!!!!!!!WD_RENAME_BACK EXCEPTION OCCURED!!!!!!!!!!!!!!!" + str(e))
                                log_Exceptions.info(f"\n---WD_RENAME_BACK_EXCEPTION_PID {cpID}:run_one_unit_process---\n{unit}\\{test}\n" + str(e)) 
                                try:
                                    shutil.rmtree(workingDir_actualName)
                                except Exception as e:
                                    log_Exceptions.info(f"\n---WD_RMTREE_EXCEPTION_PID {cpID}:run_one_unit_process---\n{unit}\\{test}\n" + str(e)) 
                                    log_Start_End_of_tests.error(f"{cpID},{covFile},WD_RMTREE_EXCEPTION_PID,{one_test}")   
                                    Exception_tests_list.info(one_test)   
                                log_Start_End_of_tests.error(f"{cpID},{covFile},WD_RENAME_BACK_EXCEPTION_PID,{one_test}")   
                                #log_Passing_tests.info(f"{testDuration_str}____{one_test}\n")
                                Passing_tests_list.info(one_test)
                                
                            
                            #covFileDictionary[covFile] = False
                        #log_Passing_tests.info(f"{testDuration_str}____{one_test}\n")
                        Passing_tests_list.info(one_test)
                        log_Start_End_of_tests.info(f"{cpID},{covFile},end,{one_test}")
                    #######################################################################################################
                except Exception as e:
                    os.chdir(setupDir)
                    print(f"{cpID}:!!!!!!!!!!!!!!!!!!!!!!!!TESTRUN EXCEPTION OCCURED!!!!!!!!!!!!!!!" + str(e))
                    log_Exceptions.info(f"\n---TESTRUN_EXCEPTION_PID {cpID}:run_one_unit_process---\n{unit}\\{test}\n" + str(e)) 
                    log_Start_End_of_tests.error(f"{cpID},{covFile},TESTRUN_EXCEPTION_PID,{one_test}")
                    Exception_tests_list.info(one_test)  
                    covFileDictionary[covFile] = False                             
                    return
                ###################################################################################################################################
                
            except Exception as e:
                print(f"{cpID}:!!!!!!!!!!!!!!!!!!!!!!!!EXCEPTION_HANDLING_FAILED IN SETUP EXCEPTION!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" + str(e))
                os.chdir(setupDir)
                log_Exceptions.info(f"\n---EXCEPTION_HANDLING_FAILED_IN_SETUP_EXCEPTION_PID {cpID}:run_one_unit_process---\n" + str(e)) 
                log_Start_End_of_tests.error(f"{cpID},{covFile},EXCEPTION_HANDLING_FAILED_IN_SETUP_EXCEPTION_PID,{one_test}")
                Exception_tests_list.info(one_test)  
                covFileDictionary[covFile] = False                
                return
            ################################################################################################################################
            print(f"{cpID}:---Child Process finished executing: {one_test}---")             
    except Exception as e:
        print(f"{cpID}:!!!!!!!!!!!!!!!!!!!!!!!!EXCEPTION_HANDLING_FAILED OCCURED!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" + str(e))       
        log_Exceptions.info(f"\n---EXCEPTION_HANDLING_FAILED {cpID}:run_one_unit_process---\n" + str(e)) 
        log_Start_End_of_tests.error(f"{cpID},{covFile},EXCEPTION_HANDLING_FAILED,{one_test}")
        try:
            one_test
        except NameError:
            log_Exception_tests.info("MISSING_TEST_NAME") 
        else:    
            log_Exception_tests.info(one_test)  
        covFileDictionary[covFile] = False                
        return

def parse_result(test ,workingDir_actualName):
    result_json = workingDir_actualName + "/result.DisplayUvmTestBench.json"
    if result_json.exists():
        with open(result_json, "r") as f:
            data = json.load(f)
            result = data.get("Result", {})
            exit_code = result.get("ToolExitCode")
            if exit_code == "0":
                print(f"{test} \n---TEST EXECUTION SUCCESSFUL---\n")
            else:
                print(f"{test} \n---TEST EXECUTION FAILED---\n")
    else:
        exit_code = "-1"
        print(f"{test} \n---JSON FILE MISSING---\n")

def scheduler(device):
    if device != "":
        device = "_"+device
    setupDir = os.getcwd()
    testListFilePath = setupDir + "\\tests"+device+".txt"
    configFilePath   = setupDir + "\\Config\\config.json"
    
    manager = multiprocessing.Manager()
    passingTestlist = manager.list()
    managedTestList = manager.list()
    ################################## Open tests.txt and read tests to run into 'managedTestList' dictonary ######################

    testListFile = open(testListFilePath, "r")
    testList = testListFile.readlines()
    testListFile.close()
    for t in testList:
        if len(t)>6:
            managedTestList.append(t)
    
    ##################### Opening config JSON file ########################
    configJson = open(configFilePath, "r+")
    config = json.load(configJson)  # Returns JSON object as a dictionary
    configJson.close()
    totalTestCount = len(managedTestList)
    noOfWrkProcs = min(config["noOfWrkProcs"], totalTestCount ,os.cpu_count())
    softwarePath = str(config["softwarePath"])
    recreate_copies_of_WorkingDir = str(config["recreate_copies_of_WorkingDir"]) == "YES" 
    ################################## Clean WorkingDirs ######################################################
    #os.system('mkdir BACKUP')
    #os.system('copy ' + setupDir + '\\GoldenCoverageWorkingDir\\* ' + setupDir + '\\BACKUP\\')
    WorkingDirsfolder = setupDir + "\\WorkingDirs\\"
    for filename in os.listdir(WorkingDirsfolder):
        file_path = os.path.join(WorkingDirsfolder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                if recreate_copies_of_WorkingDir:
                    os.unlink(file_path)
            elif os.path.isdir(file_path):
                if recreate_copies_of_WorkingDir:
                    shutil.rmtree(file_path)
        except:
            print("Unable to delete WorkingDirs")
    GoldenCoverageWorkingDirsfolder = setupDir + "\\GoldenCoverageWorkingDir\\"
    for filename in os.listdir(GoldenCoverageWorkingDirsfolder):
        file_path = os.path.join(GoldenCoverageWorkingDirsfolder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except:
            print("Unable to delete WorkingDirs")
    ######################### Copy GoldenCoverage file to GoldenCoverageWorkingDir#######################################
    try:
        os.system('copy ' + setupDir + '\\GoldenCoverage\\* ' + setupDir + '\\GoldenCoverageWorkingDir\\')
        if COVBR_ON:
            create_zerocoverage_covbr_and_its_copies(setupDir + "\\GoldenCoverageWorkingDir\\test.cov", noOfWrkProcs,setupDir,device,softwarePath)
    except Exception as e:
        print("!!!!!!!!!!!!!!!!!!!!!!!!SETUP EXCEPTION OCCURED!!!!!!!!!!!!!!!" + str(e))
        return
    ###############################################################################################################################
    ################ Make Copies of goldenCoverage file ##########################################
    goldenCovFile = ""
    for fname in os.listdir(setupDir + "\\GoldenCoverageWorkingDir"):
        goldenCovFile = fname
    os.chdir('GoldenCoverageWorkingDir')
    for i in range(noOfWrkProcs):
        shutil.copy2(setupDir + "/GoldenCoverageWorkingDir/test.cov", setupDir + "/GoldenCoverageWorkingDir/Copy{}_test.cov".format(i+1))
        if COVBR_ON:
            shutil.copy2(setupDir + "/GoldenCoverageWorkingDir/test.cov", setupDir + "/CoverageToBeMergedDir/Copy{}_test_merged.cov".format(i+1))
    #os.system(setupDir + '\\Utilities\\MultiCopy.bat ' + str(noOfWrkProcs) + ' ' + goldenCovFile)
    os.system('del /f ' + goldenCovFile)
    os.chdir(setupDir)
    BullseyeDir = os.path.dirname(setupDir)
    ###############################################################################################################
    ############################################## Setup ##########################################################
    path_files = BullseyeDir + "\\path_files\\"
    localP4VDispToolsPath = str(config["dispToolsPath"])

    try:
        if recreate_copies_of_WorkingDir:
            for i in range(noOfWrkProcs+1):
                workingDir = setupDir + "\\WorkingDirs\\workingDir_Copy{}".format(i)            
                os.system('mkdir ' + workingDir)
                os.system('copy ' + path_files + '\\* ' + workingDir)
                os.chdir(workingDir)
                #cfg2grits_version = "DISP_tools\\cfg2grits_" + projectName
                cfg2grits_version = "DISP_tools\\"+ str(config["cfg2gritsVersion"])
                print("cfg2grits_version = " + cfg2grits_version)                
                os.system('mkdir ' + cfg2grits_version)
                # os.system('copy ' + localP4VDispToolsPath + cfg2grits_version + '\\* ' + cfg2grits_version)
                os.system('copy ' + BullseyeDir + "\\" + cfg2grits_version + '\\* ' + cfg2grits_version)
                os.system('mkdir DISP_tools\\globals')
                os.system('copy ' + localP4VDispToolsPath + '\\DISP_tools\\globals\\* DISP_tools\\globals')
                os.system('mkdir DISP_tools\\defconfigs')
                os.system('copy ' + localP4VDispToolsPath + '\\DISP_tools\\defconfigs\\dg2_lmem_2gb_config_sim.xml dg2_lmem_2gb_config_sim.xml')
                os.system('copy ' + localP4VDispToolsPath + '\\DISP_tools\\defconfigs\\PlatformConfig.xml PlatformConfig.xml')
                os.system('mkdir DISP_tools\\setup')
                os.system('copy ' + localP4VDispToolsPath + '\\DISP_tools\\setup\\* DISP_tools\\setup')
                os.system('mkdir DISP_tools\\dmc_fw')
                os.system('copy ' + localP4VDispToolsPath + '\\DISP_tools\\dmc_fw\\* DISP_tools\\dmc_fw')
                os.chdir(setupDir)
    except Exception as e:
        print("!!!!!!!!!!!!!!!!!!!!!!!!SETUP EXCEPTION OCCURED!!!!!!!!!!!!!!!" + str(e))                  
        return
    ################################################## Config & Run multiprocess ##################################################
    wrkPDictList = []
    covFileList = []
    CovFileNamesMasterList = manager.list()
    covFileDictionary = manager.dict()
    for fname in os.listdir(setupDir + "\\GoldenCoverageWorkingDir"):
        covFileList.append(fname)
        CovFileNamesMasterList.append(fname)
        covFileDictionary.update({fname:False})
    ################################## Schedule first 'noOfWrkProcs' tests across 'noOfWrkProcs' wrkPs' #################################
    for wp in range(noOfWrkProcs):
        test = managedTestList[wp]
        covFile = covFileList[wp]
        wrkP = multiprocessing.Process(target=run_one_unit_process, args=(managedTestList, test, covFile, covFileDictionary, config,passingTestlist,device))
        wrkPDictList.append({'wrkP':wrkP, 'startTime':-1})
    for wrkPDict in wrkPDictList:
        wrkPDict['startTime'] = time.time()
        wrkPDict['wrkP'].start()
    ################################## 'scheduler' continues, dont't wait on started wrkPs' #############################################

    #################################################### Poll to see if a wrkP is finished #################################################
    
    while(len(managedTestList) > 0):
        while (True):
            someOneIsFree = False
            for wrkPDict in wrkPDictList:
                try:
                    if (wrkPDict['wrkP'].is_alive() == False):
                        someOneIsFree = True
                        wrkPDictList.remove(wrkPDict)
                        break
                    elif (time.time()-wrkPDict['startTime']>7000):
                        try:
                            wrkPDict['wrkP'].terminate()
                            #TODO: kill all progeny processes before killing the current
                            #TODO: check if this time durration check and kill is redundant
                            log_Exceptions.info(f"\n---TIMEOUT_EXCEPTION_PID {wrkPDict}:scheduler---\n") 
                        except Exception as e:
                            print("!!!!!!!!!!!!!!!!!!!!!!!!SCHEDULER TERMINATE EXCEPTION OCCURED!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" + str(e))       
                            log_Exceptions.info(f"\n---TERMINATE_EXCEPTION_PID {wrkPDict}:scheduler---\n" + str(e))
                except Exception as e:
                    print("!!!!!!!!!!!!!!!!!!!!!!!!SCHEDULER EXCEPTION OCCURED!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" + str(e))
                    log_Exceptions.info(f"\n---SCHEDULER_EXCEPTION---\n" + str(e))
            if someOneIsFree:
                break
        key_list = list(covFileDictionary.keys())  # key is covFileName
        val_list = list(covFileDictionary.values())  # value is bool, indicating if no updates happening on file
        position = val_list.index(False)
        covFile = key_list[position]
        if (len(managedTestList) > 0):
            test = managedTestList[0]
            wrkP = multiprocessing.Process(target=run_one_unit_process, args=(managedTestList, test, covFile, covFileDictionary, config,passingTestlist,device))            
            wrkP.start()
            wrkPDictList.append({'wrkP':wrkP, 'startTime':time.time()})
            
        
    ########################################################################################################################################

    ####### Wait until all workers have finished #####
    for wrkPDict in wrkPDictList:
        wrkPDict['wrkP'].join(7200)
        if (wrkPDict['wrkP'].is_alive()):
            try:        
                wrkPDict['wrkP'].terminate()
                #TODO: kill all progeny processes before killing the current
            except Exception as e:
                print("!!!!!!!!!!!!!!!!!!!!!!!!EXCEPTION_HANDLING OCCURED!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" + str(e))       
                Timeout_tests_list.info(f"\n---Terminated {wrkPDict['wrkP']}\n" + str(e)) 
    ##################################################
    wrkPDictList.clear()
    runDir = setupDir + "\\GoldenCoverageWorkingDir\\"
    os.chdir(runDir)
    ################################################## MERGE COVERAGE FILES ########################################################
    while(len(CovFileNamesMasterList) != 1):
        covPairList = np.array_split(CovFileNamesMasterList, int(len(CovFileNamesMasterList)/2))
        for pair in covPairList:
            yp1 = multiprocessing.Process(target=merge_cov, args=(CovFileNamesMasterList, pair, setupDir,))
            yp1.start()
            wrkPDictList.append(yp1)
        for process in wrkPDictList:
            process.join()
        wrkPDictList.clear()
    ########################## Run FBlock unit tests ################################################
    if(config["FBlockteststoggle"] == "ON"):
        os.system('rename ' + setupDir + '\\GoldenCoverageWorkingDir\\' + CovFileNamesMasterList[0] + ' ' + 'FinalCoverage.cov')
        os.system('copy ' + setupDir + '\\GoldenCoverage\\* ' + setupDir + '\\GoldenCoverageWorkingDir\\Copy_GoldenCov.cov')
        FBdestCov = 'Copy_GoldenCov.cov'
        os.environ['COVFILE'] = FBdestCov
        os.system( softwarePath + "FBlockGoogleUnitTests.exe" )
        mergedCovFile = 'FinalBullseyeCoverage.cov'
        covfiles = [f for f in os.listdir(runDir) if os.path.isfile(os.path.join(runDir, f))]
        os.system('covmerge.exe -c -f ' + mergedCovFile + ' ' + 'Copy_GoldenCov.cov' + ' ' + 'FinalCoverage.cov')
        os.system('del /f ' + 'Copy_GoldenCov.cov')
        os.system('del /f ' + 'FinalCoverage.cov')
    else :
        os.system('rename ' + setupDir + '\\GoldenCoverageWorkingDir\\' + CovFileNamesMasterList[
            0] + ' ' + 'FinalBullseyeCoverage.cov')
    ##############################################################################################################################

    ################################# Remove excluded coverage ####################################
    exclude_file = setupDir + "\\Exclude.txt"
    fread = open(exclude_file, "r")
    excludes = fread.readlines()
    os.environ['COVFILE'] = 'FinalBullseyeCoverage.cov'
    print("COVFILE : " + os.environ['COVFILE'])
    for i in excludes:
        print(i)
        os.system("covselect -a !**" + i)

    ###############################################################################################
    print(
        "################################# FINAL MERGED COV FILE ####################################################")
    print("\\GoldenCoverageWorkingDir\\FinalBullseyeCoverage.cov")
    print(
        "###########################################################################################################")

def merge_cov(CovFileNamesMasterList, covFilesList, setupDir):
    runDir = setupDir + "\\GoldenCoverageWorkingDir\\"
    os.chdir(runDir)
    file1 = covFilesList[0]
    file2 = covFilesList[1]
    random_str = str(randint(9999, 10000000))
    mergedCovFile = "merged_" + random_str + ".cov"
    CovFileNamesMasterList.remove(file1)
    CovFileNamesMasterList.remove(file2)
    CovFileNamesMasterList.append(mergedCovFile)
    os.system('covmerge.exe -c -f ' + mergedCovFile + ' ' + file1 + ' ' + file2)
    os.system('del /f ' + file1)
    os.system('del /f ' + file2)

# === MAIN ENTRY ===
if __name__ == '__main__':
    startTime = time.time()
    #log_Passing_tests.info(f"{projectName} script run started on {datetime.datetime.now()}") 

    setupDir = os.getcwd()
    ########################################### CMD ARGS ################################################
    # parser = argparse.ArgumentParser()
    # parser.add_argument('-p', '--ProcessCount', metavar='', default="10", help='Select number of process')
    # args = parser.parse_args()
    # noOfWrkProcs = int(args.ProcessCount)
    
    if(len(sys.argv)>1):
        projectName = sys.argv[1]
    os.chdir(setupDir+"\\"+projectName)
    
    device = ""
    if(len(sys.argv)>2):
        device = sys.argv[2]        
    
    
    #####################################################################################################
    ########## Run Script #########
    scheduler(device)
    ##############################
    #os.chdir(setupDir)
    os.chdir(setupDir+"\\"+projectName)
    testDuration = time.time() - startTime
    testDuration_str = time.strftime("%H hr %M min %S sec", time.gmtime(testDuration))
    print(f"The script took {testDuration_str} for {projectName} run on {date.today()}") 
    #log_Passing_tests.info(f"The script took {testDuration_str} for {projectName} run on {date.today()}") 
    
    print("###########################################################################################################")