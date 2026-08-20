# ROBENG-1886 summary

## Demo instructions

The complete installation and presentation procedure is available in:

- [demo-steps.md](demo-steps.md)

## What we achieved

We produced an installable Ubuntu 26.04 snap that packages the EtherCAT userspace and ROS 2 bridge needed for the physical EtherCAT demo. The snap uses the IgH kernel modules provided by the host and accesses the host-created `/dev/EtherCAT*` device rather than attempting to ship kernel modules itself.

The pre-migration validation artifact was:

- 192,126,976 bytes (183 MiB)
- SHA-256 `22e4a06788f9813c1ebebaf79757d0e8c790a69c1b52dd9f0105bae731b9a8e0`
- strict confinement
- built on July 20, 2026

The main packaged components are:

- IgH EtherCAT 1.6.9 userspace library and command-line tool
- ICube ROS 2 EtherCAT driver
- ROS 2 Lyrical and ROS 2 Control runtime
- controller manager and joint-state broadcaster
- EasyCAT process-data configuration
- a ROS adapter that publishes the two analog inputs on `/joint_states`
- a live terminal dashboard for the demo

## EasyCAT integration

The complete EasyCAT 32-byte output and 32-byte input process images are configured. The mapping uses the slave identity and layout confirmed during hardware testing:

- vendor ID: `0x0000079a`
- product ID: `0x00defede`
- RxPDO: `0x1600`, object `0x0005`, 32 bytes
- TxPDO: `0x1a00`, object `0x0006`, 32 bytes
- SM0: output
- SM1: input

The first two input bytes are exposed as A0 and A1. They are converted into a standard `sensor_msgs/msg/JointState` message with these names:

- `easycat_analog_0`
- `easycat_analog_1`

This gives PlotJuggler, Foxglove, and normal ROS 2 command-line tools a standard topic to consume.

## Arduino CoE/SDO memory analysis

The separate rev-2 CoE/SDO implementation was compiled for the Arduino Uno's
ATmega328P with `arduino-cli`; it was not flashed to the physical Arduino. The
final 32-byte input and 32-byte output build fits comfortably within the
board's flash and SRAM limits:

| Resource | Available | Used | Remaining |
|---|---:|---:|---:|
| Program flash | 32,256 bytes | 8,834 bytes (27.4%) | 23,422 bytes |
| SRAM | 2,048 bytes | 627 bytes (30.6%) static | 1,421 bytes for stack |
| Arduino EEPROM | 1,024 bytes | 0 bytes | 1,024 bytes |

The linked ELF accounts for the static SRAM as follows:

- 416 bytes for the complete EasyCAT object;
- 157 bytes for Arduino serial buffering and state; and
- 54 bytes for the remaining application and Arduino core globals.

The EasyCAT allocation includes both 32-byte PDO buffers, one reusable
128-byte mailbox buffer, the built-in dictionary, and all four preallocated
application SDO slots. The implementation does not use `malloc`, `new`,
Arduino `String`, or another dynamic allocation mechanism. SDO names are held
in flash, and no mailbox-sized temporary buffer is placed on the stack.

An analysis-only build with link-time optimization disabled was used to obtain
compiler stack-usage records. The largest relevant function frame was 24
bytes, `ProcessMailbox()` used 14 bytes, SDO request processing used 15 bytes,
and the largest enabled interrupt frame used 17 bytes. The estimated deepest
mailbox call chain with one interrupt is approximately 100 to 120 bytes. Even
reserving a deliberately conservative 512 bytes for the stack leaves about
909 bytes of unused SRAM.

A maximum-buffer stress build with 128-byte input and output PDOs also fit on
the Uno. It used 8,766 bytes of flash and 819 bytes of static SRAM, leaving
1,229 bytes for the stack. The deployed rev-2 profile remains 32+32 bytes, so
its margin is larger.

The generated 4,096-byte SII image is stored in the LAN9252's external EEPROM.
It consumes no Arduino flash, SRAM, or EEPROM. These results establish the
static memory and stack budget; the rev-2 CoE/SDO firmware still requires the
documented hardware validation. The physical snap demonstration described in
this summary used the hardware-validated rev-1 PDO-only profile.

## Demo experience

After installing and connecting the snap interfaces, the complete demo starts with one command:

    snap run simple-ethercat-driver-ros2.demo

This command starts the EtherCAT bridge in the background and shows a clean terminal dashboard containing live A0 and A1 values and bar graphs. At the same time, the values are published on `/joint_states`.

ROS launch output is kept out of the presentation terminal and written to:

    ~/snap/simple-ethercat-driver-ros2/current/easycat-demo.log

This supports both versions of the planned demonstration:

1. **Basic demo:** install the snap, run one command, and rotate the potentiometers while the terminal values change.
2. **Visualization demo:** show the terminal, PlotJuggler or Foxglove, and a webcam view of the board on one screen while plotting both `/joint_states` positions.

## Compatibility work

The ICube Jazzy driver required a small compatibility layer to build against ROS 2 Lyrical. The upstream source remains pinned, while the Lyrical-specific CMake changes are stored as separate, reviewable files in the snap project.

The ROS applications use Fast DDS over UDP rather than shared-memory transport. This avoids shared-memory permission errors under strict snap confinement and still allows a host visualization tool to discover `/joint_states`.

Device access is limited to `/dev/EtherCAT[0-9]*` through a `custom-device` interface. This works for local installation; Snap Store publication and automatic connection will require store review because `custom-device` is a super-privileged interface.

## Validation completed

The snap was installed and exercised in a clean Ubuntu 26.04 virtual machine. We confirmed that:

- strict snap installation succeeds
- the ROS content interface connects correctly
- the EtherCAT custom-device interface connects correctly
- the bundled EtherCAT CLI reports the pinned IgH 1.6.9 version
- ROS discovers the EasyCAT package, ICube driver, and joint-state broadcaster
- the packaged EasyCAT launch description parses successfully
- the one-command dashboard starts correctly
- the complete 32+32-byte EasyCAT configuration loads into the EtherCAT driver
- the ROS conversion path works end to end

For the data-path test, a synthetic EasyCAT message containing A0=42 and A1=211 produced:

- names: `easycat_analog_0`, `easycat_analog_1`
- positions: `42.0`, `211.0`

The original bare-metal hardware test also established that the EasyCAT board works with IgH when the host receive timeout is set to 5000 microseconds.

The exact strict snap was then exercised with the physical board in an Ubuntu
26.04 VM using the distribution's external IgH kernel modules. The confined
userspace stack:

- discovered `Generic 32+32 bytes rev 1` with the bundled CLI;
- moved the slave to OP;
- completed the 64-byte process domain with WorkingCounter 3/3;
- displayed live A0/A1 values from both physical dials;
- published both values on `/joint_states`; and
- supplied both live curves to PlotJuggler over ROS 2 DDS.

The Arduino ran the rev-1 extended validation firmware from the separate
`canonical/ethercat-easycat-testing-repo` at commit
`67e36f641bf90a472ac88ed1969bbfa6cc2792c6`.

## Completion status

The implementation and acceptance test are complete. All EtherCAT userspace
requirements used by the ROS 2 bridge are supplied by the snap, while the
kernel master and device node remain host responsibilities as required.
