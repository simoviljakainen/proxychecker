import argparse, sys, textwrap
import requests, json
from queue import Queue
from threading import Thread, Lock

def init(testUrl, timeOut):
    global TEST_URL, TIMEOUT, SEPARATOR
    TEST_URL, TIMEOUT = testUrl, timeOut
    SEPARATOR = "+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+"

def loadProxy(fileIn):
    try:
        with open(fileIn, "r") as file:
            for line in file:
                yield line

    except FileNotFoundError:
        print("File not found.")
        exit(1)

    except Exception as e:
        print(f"There was a problem with the input file:\n{e}")
        exit(1)

def isWorking(httpsProxy):
    
    proxies = {"https" : f"https://{httpsProxy}"}

    try:
        results = requests.get(url=TEST_URL, proxies=proxies, timeout=TIMEOUT)

    except requests.exceptions.ProxyError:
        print("Proxy connection failed. Your IP might be suspended.")
        return False

    except requests.exceptions.ConnectTimeout:
        print("Request timed out. Slow or non-responsive proxy.")
        return False

    except requests.exceptions.InvalidProxyURL:
        print("Invalid proxy URL.")
        return False

    if(httpsProxy.split(":")[0] != json.loads(results.text)['origin']):
        print("Response IP is not the same as the proxy IP.")
        return False

    if(results.status_code != 200):
        print("Request failed.")
        return False

    return True

def processProxy(lock, q, out, counter):
    while True:
        httpsProxy = q.get()

        # Save working proxy
        if(isWorking(httpsProxy)):
            with lock:
                out.write(httpsProxy + '\n')
                counter[0] += 1

        q.task_done()

def main(fileIn, fileOut, threads):
    q = Queue()
    lock = Lock()
    counter = [0]

    with open(fileOut, "w") as out:

        for _ in range(threads):
            thread = Thread(target=processProxy,
                args=(lock, q, out, counter)
            )

            # Daemon thread dies after main thread dies
            thread.daemon = True
            thread.start()

        # Insert proxies into queue
        for num, proxyline in enumerate(loadProxy(fileIn), start=1):
            q.put(proxyline.strip())

        else:
            print(
                f"\nAdded {num} proxies into queue. "
                f"Starting the checking process with {threads} threads.\n\n"                
                f"{SEPARATOR}\nThread output\n{SEPARATOR}\n"
            )

        # Main thread waits until the queue has been processed
        q.join()

    try:
        print(
            f"\n{SEPARATOR}\nDone\n{SEPARATOR}\n"
            f"\nOut of {num} proxies, {counter[0]} were good "
            f"({round((counter[0] / num) * 100, 2)}%).\n"
        )

    except ZeroDivisionError:
        print("No proxies were processed.")

if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        prog='proxycheck.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
        '''
                  HTTPS proxy checker.
            --------------------------------
                 _._     _,-'""`-._
                (,-.`._,'(       |\`-/|
                    `-.-' \ )-`( , o o)
                          `-    \`_`"'-
       ''')
    )      
    parser.add_argument('infile', nargs='?', default="in.txt",
                    help='Input file. Every line has a HTTPS proxy in IP:Port format.')
    parser.add_argument('-o', '--output', nargs='?', default='out.txt',
                    help='Ouput file. Every line has a working HTTPS proxy in IP:Port format.')
    parser.add_argument('-t', '--threads', nargs='?', default=1, type=int,
                    help='Number of threads. By default the checking process is single threaded.')
    parser.add_argument('-u', '--url', nargs='?', default='https://httpbin.org/ip',
                    help='Test URL. By default https://httpbin.org/ip is used.\
                         Note that request IP JSON response is needed.')
    parser.add_argument('-s', '--timeout', nargs='?', default=10, type=int,
                    help='Seconds required to timeout a request.')

    arg = parser.parse_args()

    # Initialize global constants
    init(arg.url, arg.timeout)

    # Start main thread
    main(arg.infile, arg.output, arg.threads)
