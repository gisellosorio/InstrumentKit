from sys import platform
from time import sleep
from instruments.qubitekk import MC1


def main():
    """
    Runs the switch program on its own, as a test
    :return:
    """
    if platform == "linux" or platform == "linux2":
        port = "/dev/ttyUSB0"
    else:
        port = "COM1"
    mc1 = MC1.open_serial(port, 9600, timeout=1)

    print("Firmware", mc1.firmware)
    print("Motor controller type: ", mc1.controller)
    print("centering")
    mc1.center()
    while mc1.is_centering():
        pass
    print("Stage Centered")
    # for the motor in the mechanical delay line, the travel is limited from
    # the full range of travel. Here's how to set the limits.
    mc1.lower_limit = -260
    mc1.upper_limit = 300
    mc1.increment = 5
    for x_pos in mc1.range:
        print(str(mc1.position)+" "+str(mc1.direction))
        mc1.move(x_pos)
        while mc1.move_timeout > 0:
            sleep(0.5)


if __name__ == "__main__":
    main()