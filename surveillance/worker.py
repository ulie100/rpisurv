import time
import subprocess
import platform
import os
import shlex
import signal
from setuplogging import setup_logging

def worker(name,rtsp_url,omxplayer_extra_options,coordinates,stopworker):
    def start_subprocess(rtsp_url,coordinates):
        command_line='/usr/bin/omxplayer --live --timeout 60 --aidx -1 -o hdmi' + ' ' + omxplayer_extra_options + ' ' +  rtsp_url + ' --win ' + '"' + " ".join(map(str,coordinates)) + '"'
        command_line_shlex=shlex.split(command_line)
        logger.debug("Starting stream " + name + " with commandline " + str(command_line_shlex))
        #The other process is just to be able to develop/simulate on a Windows or OSX machine
        if platform.system() == "Windows":
            proc=subprocess.Popen('echo this is a subprocess started with coordinates ' + str(coordinates) + '& ping 192.168.0.160 /t >NUL', shell=True)
        elif platform.system() == "Linux":
            proc=subprocess.Popen(command_line_shlex,preexec_fn=os.setsid,stdin=subprocess.PIPE)
        else:
            proc=subprocess.Popen('echo this is a subprocess started with coordinates ' + str(coordinates), shell=True)
        return proc

    def stop_subprocess(proc):
        #The other process is just to be able to develop on a Windows or OSX machine
        if platform.system() == "Windows":
            proc.kill()
        else:
            #This kill the process group so including all children
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            proc.wait()

    #Ctrl-C handling
    def signal_sigint_handler(signum,frame):
        logger.info("Ctrl C was pressed")
        stopworker.value = True
    def signal_sigterm_handler(signum,frame):
        logger.info("This process was sigtermed")
        stopworker.value = True

    signal.signal(signal.SIGINT, signal_sigint_handler)
    signal.signal(signal.SIGTERM, signal_sigterm_handler)

    #Logger setup
    logger = setup_logging( "logs/" + name + ".log",__name__)
    logger.debug("logger from " + name)

    #Start stream and watchdog
    attempts=0
    proc=start_subprocess(rtsp_url,coordinates)
    while attempts < 100000 and stopworker.value == False:
        if proc.poll() != None:
            proc.communicate(input="\n")
            proc=start_subprocess(rtsp_url,coordinates)
            attempts = attempts + 1
            #Wait for omxplayer to crash, or not
            time.sleep(10)
            logger.info("Trying to restart" + name +" attempts:" + str(attempts))
        else:
            attempts=0
        time.sleep(5)

    #If we come to this point, we are instructed to kill this stream
    stop_subprocess(proc)
    logger.info("This stream has been stopped")
