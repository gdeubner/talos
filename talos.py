#https://www.bc-robotics.com/tutorials/sending-email-attached-photo-using-python-raspberry-pi/
from gpiozero import MotionSensor, CPUTemperature
from picamera import PiCamera, Color
import time, datetime, signal, sys, os, smtplib, ssl, httplib, subprocess, re, pdb
 
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

SMTP_SERVER = 'smtp.gmail.com' 
SMTP_PORT = 587 
GMAIL_USERNAME = '' #holds email used to send emails and upload to google drive
GMAIL_PASSWORD = '' #holds corresponding password
MODE = None
NOTIFY = '' #indicate wish to send email notification
EMAIL = '' #email to deliver to 
UPLOAD = '' #indicates desire to uplaod content to google drive

count = 0
timer_start = 0
start_time_and_date = ''
ethernet = False
modes = ['log', 'pic', 'vid']


class configPrefs:
    '''for storing user preference configuration while running'''
    def __init__(self, user = None, pswrd = None, mode = None, notify = None, email = None, upload = None):
        self.user = user
        self.pswrd = pswrd
        self.mode = mode
        self.notify = notify
        self.email = email
        self.upload = upload
        
def extractModes(str):
    '''takes the 'Modes' line from .config and returns a list of the modes'''
    list = re.findall('\w*' ,str)
    list2 = []
    del list[0]
    for e in list:
        if e is not '':
            list2.append(e)
    print list2
    return list2

def readConfiguration():
    '''reads in preferences for running this program, such as taking video/pictures/log file, or notification preferences'''
    global GMAIL_USERNAME
    global GMAIL_PASSWORD
    global EMAIL
    global MODE
    global NOTIFY
    global UPLOAD

    fd = open('/home/pi/Documents/talos/.config', 'r')
    match = re.search('User: (.*)' ,fd.readline())
    GMAIL_USERNAME = match.group(1)
    match = re.search('Password: (.*)' ,fd.readline())
    GMAIL_PASSWORD = match.group(1)
    MODE = extractModes(fd.readline())

    match = re.search('Notifications: (.*)' ,fd.readline())
    NOTIFY = match.group(1)
    match = re.search('Recieving: (.*)' ,fd.readline())
    EMAIL = match.group(1)
    match = re.search('Upload: (.*)' ,fd.readline())
    UPLOAD = match.group(1)

    return configPrefs(GMAIL_USERNAME, GMAIL_PASSWORD, EMAIL, MODE, NOTIFY, UPLOAD)
    
def printConfiguration():
    '''Prints credentials read from .config. Used for testing'''
    global GMAIL_USERNAME
    global GMAIL_PASSWORD
    global EMAIL
    global MODE
    global NOTIFY
    global UPLOAD

    print """
user: {}
password: {}
email: {}
mode: {}
notifications: {}
uplaod pref: {}
""".format(GMAIL_USERNAME, GMAIL_PASSWORD, EMAIL, MODE, NOTIFY, UPLOAD)
    
def configure():
    '''Reads in user's preferences for how Talos should run when monitoring. prefs saved in .config'''
    if os.path.isfile('/home/pi/Documents/talos/.config'):
        while True:
            confirm = raw_input('.config file already exists. Would you like to overwrite it?\n yes/no: \n')
            if confirm.lower()  == 'no':
                print 'Configuration cancelled'
                return
            elif confirm.lower() == 'yes':
                os.system('rm /home/pi/Documents/talos/.config')
                break
            else:
                print 'Invalid response.'

    user = ''
    pswd = ''    
    notify = ''
    rec = ''
    upload = ''
    modesStr=''
    while True:
            user = raw_input('Enter user email address or "guest":\n(Note: Must be gmail and must have "Less secure apps" enabled) \n')
            if re.search('.+@gmail.com', user):
                break
            elif user == 'guest' or user == '':
                user = 'guest'
                pswd = 'n/a'
                notify = 'no'
                rec = 'n/a'
                upload = 'no'
                break
            print 'Invalid email address'
    if user is not 'guest':
        
        #user password
        pswd = raw_input('Enter user email\'s password\n')


        #notifications / recieving email address
        while True:
            notify = raw_input('Would you like notifications activated? [yes/no]\n')
            if notify == 'yes':
                while True:
                    rec = raw_input('Enter the email address you wish to recieve notifications: \n')
                    if re.search('.+@.+\..+', rec):
                        break
                    print 'Invalid email address'
                break
            elif notify == 'no':
                break
            print 'Invalid response'
            

        #upload to drive
        while True:
            upload = raw_input('Would you like to upload your surveilance to google drive? [yes/no]\n')
            if upload == 'yes':
                break
            if upload == 'no':
                break
            print 'Invalid response'
        
    #mode
    while True:
        modesStr = raw_input('Enter one or more modes. Options: ' + getModes() + '\n')
        l = modesStr.split(' ')
        valid = True
        for mode in l:
            if mode not in modes:
                print 'Invalid mode entered.'
                valid = False
                break
        if valid:
            break

    #write configuration to .config
    fd = open('/home/pi/Documents/talos/.config', 'w') 
    fd.write('User: '+ user + '\nPassword: ' + pswd + '\nMode: '+ modesStr + '\nNotifications: ' + notify + '\nRecieving: ' + rec + '\nUpload: ' + upload)
    fd.close()

def getModes():
    '''returns modes saved in .config as a string'''
    str = ''
    for mode in modes:
        str = str + mode + ' '
    return str


def clear_configuration():
    '''deletes .config file'''
    while True:
            confirm = raw_input('Are you sure you want to delete your configuration? [yes/no]\n')
            if confirm.lower()  == 'no':
                print 'Configuration not deleted'
                return
            elif confirm.lower() == 'yes':
                break
            else:
                print 'Invalid response.'
    if os.path.isfile('/home/pi/Documents/talos/.config'):
        os.system('rm /home/pi/Documents/talos/.config')
        print '.config file removed'
    else:
        print 'No .config file found'

def get_space():
    '''returns a tuple with current information about the system like space used, unused, ect.'''
    df = subprocess.Popen(["df", '-h', "/"], stdout=subprocess.PIPE)
    output = df.communicate()[0]
    device, size, used, available, percent, mountpoint = \
        output.split("\n")[1].split()
    return (device, size, used, available, percent, mountpoint)
    
    
def connected():
    '''determines if system is connected to the internet by contacting www.google.com'''
    conn = httplib.HTTPConnection("www.google.com", timeout=5)
    try:
        conn.request("HEAD", "/")
        conn.close()
        return True
    except:
        conn.close()
        return False


class Emailer:
    '''class used for sending an email notification'''
    def sendmail(self, recipient, subject, content, image):
          
        #Create Headers
        emailData = MIMEMultipart()
        emailData['Subject'] = subject
        emailData['To'] = recipient
        emailData['From'] = GMAIL_USERNAME

        #Attach our text data  
        emailData.attach(MIMEText(content))

        #Create our Image Data from the defined image
        imageData = MIMEImage(open(image, 'rb').read(), 'jpg') 
        imageData.add_header('Content-Disposition', 'attachment; filename="'+image+'"')
        emailData.attach(imageData)
        
        #Connect to Gmail Server
        session = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        session.ehlo()
        session.starttls()
        session.ehlo()
  
        #Login to Gmail
        session.login(GMAIL_USERNAME, GMAIL_PASSWORD)
  
        #Send Email & Exit
        session.sendmail(GMAIL_USERNAME, recipient, emailData.as_string())
        session.quit
  
sender = Emailer()
    
def send_email(f):
    '''sends email to predetermined email address'''
    if not ethernet:
        os.system('ifconfig wlan0 up')
        print 'Connecting to internet'
    sendTo = 'gdeubner@gmail.com'
    emailSubject = "Talos: Motion was detected"
    emailContent = "Talos has detected motion at " + str_now() + '\n'+summary('Current')
    t1 = int(time.time())
    t2 = int(time.time())
    while not connected() and t2-t1 < 120:
        t2 = int(time.time())
    if t2-t1 >= 120:
        print 'Connection failed, email not sent'
        return
    if not ethernet:
        print 'Connected'
    sender.sendmail(sendTo, emailSubject, emailContent, f)
    print 'Email sent'
    if not ethernet:
        os.system('ifconfig wlan0 down')
        print 'Disconnected'

def summary(str):
    '''prints a summary of system to console. (temp, memory, # of detections)'''
    cpu = CPUTemperature()
    spc = get_space()
    str ="""----SUMMARY----
Start time: {}
{} time: {}
Duration: {}
Detections: {}
Space on device: {}, Space used: {}, Space free: {}
CPU Temperature: {}C, (recomended temp: -40C to 85C)
    """.format(start_time_and_date, str, str_now(), timer(timer_start, time.time()), count, spc[1], spc[2], spc[3], cpu.temperature)
    return str

    
def timer(start, finish):
    '''given start and end times in seconds, returns a string of total hours, minutes, and seconds elapsed'''
    t = finish - start
    hours = int(t/3600)
    minutes = int((t%3600)/60)
    seconds = int((t%3600)%60)
    return str(hours) + ' hours, '+ str(minutes)+' minutes, and ' +str(seconds) +' seconds'
    

def sighandl(signum, frame):
    '''handles sigsegfault'''
    print '\nmonitoring stopped'
    print summary('End')
    new_log_entry('End    ','')
    sys.exit()


def to_str(num, l):
    '''prepends '0' to num until it creates a string of length l'''
    s = str(num)
    while len(s)<l:
        s = '0'+s
    return s

def str_now():
    d = datetime.datetime.now()
    return ''.join((to_str(d.month,2),'-',to_str(d.day,2),'-',str(d.year),'|',to_str(d.hour,2),':',to_str(d.minute,2),':',to_str(d.second,2)))
    
def new_log_entry(action, mode):
    '''creates a new date/time/action entry in the logfile'''
    fd = open('/home/pi/Documents/talos/logfile.txt', 'a+')
    d = datetime.datetime.now()
    fd.write(''.join((to_str(d.month,2),'/',to_str(d.day,2),'/',str(d.year),'\t',to_str(d.hour,2),':',to_str(d.minute,2),':',to_str(d.second,2), '\t', action, '\t\t', mode,'\n')))
    fd.close()



def take_pic(cam):
    '''takes a picture and saves it'''
    if not os.path.isdir('/home/pi/Documents/talos/pics-talos'):
        os.makedirs('/home/pi/Documents/talos/pics-talos')
    cam.rotation = 0
    #cam.start_preview()
    cam.annotate_text_size = 64
    cam.annotate_text = str_now()
    cam.annotate_background = Color.from_rgb(0,0,0)
    #time.sleep(.5)
    image = '/home/pi/Documents/talos/pics-talos/img'+str_now()+'.jpg'
    cam.capture(image)
    #cam.stop_preview()
    return image

def take_vid(cam, pir):
    '''takes a video while movement is detected'''
    duration = 10
    if not os.path.isdir('/home/pi/Documents/talos/vids-talos'):
        os.makedirs('/home/pi/Documents/talos/vids-talos')
    vid_list = []
    cam.rotation = 0
    cam.annotate_text_size = 64
    cam.annotate_background = Color.from_rgb(0,0,0)
    cam.annotate_text = str_now()
    cam.start_preview()
    vid = '/home/pi/Documents/talos/vids-talos/vid'+str_now()+'.h264'
    cam.start_recording(vid)
    vid_list.append(vid)
    timer = 0
    timer2 = 0
    while timer < duration:
        cam.annotate_text = str_now()
        time.sleep(1)
        if pir.motion_detected:
            timer = 0
        else:
            timer += 1
        timer2 += 1
        if timer2 >= 300:
            cam.stop_recording()
            vid = '/home/pi/Documents/talos/vids-talos/vid'+str_now()+'.h264'
            cam.start_recording(vid)
            vid_list.append(vid)
    cam.stop_recording()
    cam.stop_preview()
    return vid_list

def instruc():
    '''prints instructions to console'''
    print """TALOS - your very own sentry 
    Modes:
    [sudo] python talos.py [config/log/pic/vid] [email]
    
    config mode: Creates a .config file which stores the emails and 
    passwords used to send notifications when camera is activated.
    (Must run as sudo to send email notifications)
    
    clear_config mode: Talos will delete your .config file

    log mode: Talos will keep a log file of each time the motion
    sensor is tripped.

    pic mode: Talos will take a picture when motion sensor is 
    tripped as well as keeping a log file.

    vid mode: Talos will take a video when motion sensor is tripped
    as well as keeping a log file.
    """

def modeToStr(mode):
    '''returns a string containing the modes in .config'''
    mode_str = ''
    for m in mode:
        mode_str = mode_str + m
    return mode_str


def monitor():
    '''runs monitoring software based on configurations saved in .config file'''
    global count
    global timer_start
    global start_time_and_date
    global MODE

    #pdb.set_trace()
    
    #time.sleep(60)
    signal.signal(signal.SIGINT, sighandl)
    timer_start = time.time()
    start_time_and_date = str_now()
    if 'log' in MODE:
        fd = open('/home/pi/Documents/talos/logfile.txt', 'a+')
        fd.seek(0)
        if not fd.read(1):
            fd.write('Date:\t\tTime:\t\tAction:\t\tMode:\n')
        fd.close()
    pir = MotionSensor(4,queue_len = 1)
    if 'log' in MODE:
        new_log_entry('Start ','')
    print 'monitoring'
    cam = PiCamera()
    os.system('ifconfig wlan0 down') #turns off wifi card to conserve energy
    global ethernet
    ethernet = connected()
    while True:
        while not pir.motion_detected: #just loops until motion is detected
            x=1
        print 'Motion detected'
        count += 1
        img = None
        vid = None
        if 'log' in MODE:
            new_log_entry('Motion', modeToStr(MODE))
        if 'pic' in MODE:
            img = take_pic(cam)
        if 'vid' in MODE:
            vid_list = take_vid(cam, pir)
        if NOTIFY is 'yes':
            send_email(img)
        #if UPLOAD is 'yes':
        #    upload(img, vid_list)

        pir.wait_for_no_motion()    

def noConfigFile():
    '''prints a welcome and error message, then calls configure method'''
    print 'Welcome to Talos, your personal sentinel.\nNo config file was found.\nEntering configuration mode.'
    configure()

    
def main():
    global modes
    unrecognized_input = 'Unrecognized input. Enter "python talos.py instructions" for help.'
    
    if len(sys.argv) is 1:
        if os.path.isfile('/home/pi/Documents/talos/.config'):
            configPrefs = readConfiguration()
            monitor()
        else:
            noConfigFile()
    elif len(sys.argv) is 2:
        if sys.argv[1] == 'config':
            configure()
        elif sys.argv[1] == 'clear_config':
            clear_configuration()
        elif sys.argv[1] == 'instructions':
            instruc()
        else:
            print unrecognized_input
    else:
        print unrecognized_input


    return


if __name__ == '__main__':
    main()
