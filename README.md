# talos
You very own personal sentry.

    To run:
    [sudo] python talos.py (optional:[-config, -clear_config, -instructions])
    Running the command "sudo python talos.py" will have Talos read in the user
    preferences from the .congfig file and begin monitoring based on those 
    preferences.
    config tag: program will prompt the user for information about how the 
    program should run. This information is saved in a .config file. The 
    following will be asked:
    
    * User email address - used to send email notifications when the motion sensor
      is tripped. Enter guest to skip this option. 
      (Note: Must have "Less Secure Apps" enabled)
    * Password - the corresponding user email password
    
    * Notifications - entering yes will allow Talos to send you email notifications
      when th motion sensor is tripped with a picture of what tripped it (if 
      pictures are enabled) along with basic information about the computer running 
      the program like storage space and cpu temperature.
    * Email Notified - the email Talos will send your notifications to.
    * Upload to drive - This option is currently under construction.
    * Modes - you may enter any combination of the modes: log, vid, pic to
      specify what you would like Talos to do when motion is detected.
    
    clear_config tag: Talos will promt you to make sure you want to delete your
    .config file, then delete the file.
