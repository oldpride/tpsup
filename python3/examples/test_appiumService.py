from appium.webdriver.appium_service import AppiumService

service = AppiumService()

args = [
    #"--address", "127.0.0.1",  # this works
    "--address", "0.0.0.0",  # this works on command line but not in this script. Why?
    "--port", "4723",
    "--log-no-colors",
    "--base-path", '/wd/hub'
]

print(f"starting cmd = appium {' '.join(args)}")
service.start(args=args)
print(f"started")
print(f"service.is_running={service.is_running}")
print(f"service.is_listening={service.is_listening}")
service.stop()
