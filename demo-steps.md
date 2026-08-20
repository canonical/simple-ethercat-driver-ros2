# EtherCAT ROS 2 Bridge — step-by-step runbook

This runbook reproduces the physical validation completed on July 21, 2026. It
assumes the host is running Ubuntu 26.04 and the EasyCAT firmware already
contains the validated 32-byte input and 32-byte output process image.

## What the demo shows

The snap reads the Arduino's A0 and A1 analog inputs and presents the same data
in two places. On the supplied device, the two dials on the top-mounted EasyCAT
Test shield are potentiometers already connected to those inputs:

- a live terminal dashboard showing A0 and A1 from 0 to 255;
- the ROS 2 `/joint_states` topic, ready for PlotJuggler or Foxglove.

The published joint order is fixed:

1. `easycat_analog_0` — `/joint_states.position[0]`
2. `easycat_analog_1` — `/joint_states.position[1]`

## 1. Prepare the hardware

1. Connect the EasyCAT EtherCAT port to the host's configured EtherCAT network
    adapter.
2. Connect and power the Arduino/EasyCAT board.
3. Confirm the EasyCAT Test shield is seated on top. Its two black dials are the
    potentiometers used by the demo; no external parts or wiring are required.
4. Wait a few seconds for the board and network adapter to initialize.

## 2. Open the snap project directory

    cd ~/Documents/26.10/ethercat/simple-ethercat-driver-ros2

The expected artifact is:

    simple-ethercat-driver-ros2_0.1_amd64.snap

Check that it exists:

    ls -lh simple-ethercat-driver-ros2_0.1_amd64.snap

## 3. Verify the host EtherCAT master

The host must supply the IgH kernel modules and `/dev/EtherCAT0`. The EasyCAT
setup also requires the previously validated IgH receive timeout of 5000
microseconds.

Check the device node:

    sudo ls -l /dev/EtherCAT0

Check that the host master sees the slave:

    sudo ethercat slaves

Expected slave description:

    Generic 32+32 bytes rev 1

Do not continue until the slave is visible. If it is missing, check board power,
the EtherCAT cable, the selected network adapter, the IgH modules, and the
5000 µs timeout.

## 4. Install the ROS 2 content snap

Check whether the Lyrical content snap is already installed:

    snap list ros-lyrical-ros-base

If it is not installed, install the edge build used by this project:

    sudo snap install ros-lyrical-ros-base --edge

## 5. Install the demo snap

Install or refresh the locally built artifact:

    sudo snap install --dangerous ./simple-ethercat-driver-ros2_0.1_amd64.snap

Using `--dangerous` is expected for a local snap that has not been signed by the Snap Store.

## 6. Connect the snap interfaces

Connect the ROS 2 content provider:

    sudo snap connect \
        simple-ethercat-driver-ros2:ros-lyrical-ros-base \
      ros-lyrical-ros-base:ros-lyrical-ros-base

Connect access to `/dev/EtherCAT*`:

    sudo snap connect \
            simple-ethercat-driver-ros2:ethercat-master \
            simple-ethercat-driver-ros2:ethercat-master-slot

Verify the result:

    snap connections simple-ethercat-driver-ros2

The `ros-lyrical-ros-base`, `ethercat-master`, `network`, and `network-bind` plugs should all have connected slots.

## 7. Verify the bundled EtherCAT command

Confirm the packaged IgH version:

    snap run simple-ethercat-driver-ros2.ethercat version

Expected version: IgH EtherCAT master 1.6.9 from the pinned stable-1.6 revision.

Confirm that the confined command can see the EasyCAT slave:

    snap run simple-ethercat-driver-ros2.ethercat slaves

Expected slave description:

    Generic 32+32 bytes rev 1

## 8. Run the basic terminal demo

Start the complete bridge and terminal dashboard:

    snap run simple-ethercat-driver-ros2.demo

Wait for the dashboard status to change from:

    WAITING FOR ETHERCAT DATA

to:

    LIVE

Rotate the first potentiometer. A0 and its bar graph should change. Rotate the second potentiometer. A1 and its bar graph should change independently.

Stop the demo with Ctrl-C.

## 9. Verify `/joint_states`

Leave the terminal demo running and open a second terminal.

Display the ROS messages:

    snap run simple-ethercat-driver-ros2.ros2 topic echo /joint_states

The output should contain:

    name:
    - easycat_analog_0
    - easycat_analog_1
    position:
    - <A0 value>
    - <A1 value>

Optionally check the publication rate:

    snap run simple-ethercat-driver-ros2.ros2 topic hz /joint_states

Rotate both potentiometers and confirm that the two position values change.

## 10. Run the PlotJuggler or Foxglove demo

1. Keep `snap run simple-ethercat-driver-ros2.demo` running.
2. Start PlotJuggler or Foxglove on the host with ROS 2 domain 0.
3. Select the `/joint_states` topic.
4. Plot `/joint_states/position[0]` and label it A0.
5. Plot `/joint_states/position[1]` and label it A1.
6. Rotate the potentiometers and verify that both curves respond independently.

The snap uses Fast DDS over UDPv4, so a host ROS 2 visualization tool can discover the topic without an additional bridge process.

## 11. Record the final video

Arrange these windows on one screen:

- the EasyCAT terminal dashboard;
- PlotJuggler or Foxglove with both curves visible;
- the webcam view showing the board and potentiometers.

Start screen recording, rotate each potentiometer separately, then rotate both. Make sure the physical movement, terminal values, and plotted curves are visible at the same time.

## Troubleshooting

### Dashboard says `WAITING FOR ETHERCAT DATA`

Allow up to 15 seconds for ROS startup. If it does not become live, inspect the log:

    cat ~/snap/simple-ethercat-driver-ros2/current/easycat-demo.log

### Dashboard says `NO DATA - CHECK DEVICE/LOG`

The ROS processes started, but no complete A0/A1 message arrived. Check the slave state and log:

    snap run simple-ethercat-driver-ros2.ethercat slaves
    tail -n 100 ~/snap/simple-ethercat-driver-ros2/current/easycat-demo.log

### Dashboard says `BRIDGE STOPPED - CHECK LOG`

The controller manager stopped. Inspect:

    tail -n 200 ~/snap/simple-ethercat-driver-ros2/current/easycat-demo.log

Then verify the interface connections and device:

    snap connections simple-ethercat-driver-ros2
    sudo ls -l /dev/EtherCAT0
    sudo ethercat slaves

### PlotJuggler cannot see `/joint_states`

1. Confirm the terminal demo says `LIVE`.
2. Confirm the snap ROS CLI can see the topic:

    snap run simple-ethercat-driver-ros2.ros2 topic list

3. Ensure PlotJuggler uses ROS domain 0.
4. Ensure no shell variable sets a different `ROS_DOMAIN_ID`.
5. Restart PlotJuggler after the demo is running.

## Fast rehearsal checklist

- [ ] Board powered and EtherCAT cable connected
- [ ] `sudo ethercat slaves` shows `Generic 32+32 bytes rev 1`
- [ ] Final snap installed
- [ ] ROS content and EtherCAT interfaces connected
- [ ] Packaged EtherCAT CLI sees the slave
- [ ] Dashboard reaches `LIVE`
- [ ] A0 changes with potentiometer 1
- [ ] A1 changes with potentiometer 2
- [ ] `/joint_states` contains both names and positions
- [ ] PlotJuggler or Foxglove shows both curves
- [ ] Webcam framing and screen recording tested
