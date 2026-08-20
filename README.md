# EtherCAT ROS 2 bridge snap

A strict Ubuntu 26.04 snap that packages IgH EtherCAT userspace, the ICube ROS
2 EtherCAT driver, and a ready-to-run EtherCAT demonstration for ROS 2 Lyrical.

Connect an EasyCAT board, install the snap, and run one command to:

- start the EtherCAT ROS 2 Control hardware interface;
- read both EasyCAT analog inputs;
- publish them as standard ROS 2 joint positions on `/joint_states`; and
- display A0 and A1 in a clean live terminal dashboard.

```text
EasyCAT board
  └─ 32-byte TxPDO / 32-byte RxPDO
    └─ host IgH kernel master and /dev/EtherCAT0
      └─ strict simple-ethercat-driver-ros2 snap
        ├─ ROS 2 Control + GenericEcSlave
        ├─ /joint_states
        └─ live A0/A1 terminal dashboard
```

## Quick links

- [Step-by-step demo runbook](demo-steps.md)
- [Reproducibility guide](reproducibility-guide.md)
- [Project summary](summary.md)

## Project status

Completed:

- reproducible `core26` snap build;
- pinned IgH 1.6.9 userspace library and CLI, without kernel modules;
- pinned ICube EtherCAT ROS 2 driver built for ROS 2 Lyrical;
- complete EasyCAT 32-byte input and output process images;
- strict `/dev/EtherCAT*` access through `custom-device`;
- A0/A1 conversion to `sensor_msgs/msg/JointState`;
- one-command terminal dashboard;
- strict installation and runtime checks on a clean Ubuntu 26.04 VM;
- synthetic end-to-end ROS validation with A0=42 and A1=211; and
- physical validation through the strict snap: slave discovery, OP state,
  WorkingCounter 3/3, live A0/A1 values, `/joint_states`, and PlotJuggler.

## Packaged components

| Component | Version/source | Purpose |
|---|---|---|
| Snap base | `core26` | Ubuntu 26.04 runtime |
| ROS 2 | Lyrical Luth | ROS runtime and DDS communication |
| IgH EtherCAT | 1.6.9, commit `beb2bf07df4a19024490c0517137cffa8f97ace0` | Userspace API, `libethercat`, and CLI |
| ICube EtherCAT driver | commit `7a32bd7b8fc066c6668b1df7446c89aff570bb7d` | ROS 2 Control integration |
| GenericEcSlave | ICube plugin | YAML-driven EasyCAT PDO mapping |
| EasyCAT adapter | This repository | Converts A0/A1 to `/joint_states` |
| Terminal monitor | This repository | Starts the stack and displays live values |

The host provides the `ec_master` kernel module, NIC driver, and
`/dev/EtherCAT*`. No kernel module or NIC driver is built into the snap.

## Demo result

The snap provides a one-command EtherCAT demo. It starts the EtherCAT ROS 2
Control bridge, maps the two analog inputs to ROS joint positions, publishes
`/joint_states`, and displays a live terminal dashboard:

```bash
snap run simple-ethercat-driver-ros2.demo
```

The dashboard shows `A0` and `A1` as values from 0 to 255 with live bar graphs.
Its status changes to `LIVE` after complete data begins arriving. Bridge logs
are kept out of the presentation terminal and written to:

```text
~/snap/simple-ethercat-driver-ros2/current/easycat-demo.log
```

## Supported EasyCAT process image

| Property | Value |
|---|---|
| Vendor ID | `0x0000079a` |
| Product ID | `0x00defede` |
| RxPDO | `0x1600`, object `0x0005`, 32 bytes |
| TxPDO | `0x1a00`, object `0x0006`, 32 bytes |
| SM0 | output / RxPDO, watchdog enabled |
| SM1 | input / TxPDO, watchdog disabled |
| Mailbox protocols | none |

All 64 process-data entries are declared to preserve the exact slave layout.
TxPDO bytes 0 and 1 are exposed as `analog_input_0` and `analog_input_1`.

## Prerequisites

For building:

- Snapcraft 9;
- LXD; and
- access to the ROS package archive and pinned source repositories.

For running:

- Ubuntu 26.04;
- the host IgH EtherCAT master and NIC driver;
- the `ros-lyrical-ros-base` content snap; and
- an EasyCAT board using the process image above.

## Build

The Lyrical extension is experimental in Snapcraft 9 and must be explicitly
enabled:

```bash
git clone https://github.com/canonical/simple-ethercat-driver-ros2.git
cd simple-ethercat-driver-ros2
SNAPCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=1 snapcraft pack --use-lxd
```

Expected amd64 artifact:

```text
simple-ethercat-driver-ros2_0.1_amd64.snap
```

The clean renamed build produced a 192,204,800-byte (183 MiB) artifact with
SHA-256:

```text
94db0fe7b64bbb9a07bf469ae4a77bf0aedfe3406f873d31055ef8df0822cd38
```

## Install and connect the EtherCAT device

Install the Lyrical content provider if it is not already present:

```bash
sudo snap install ros-lyrical-ros-base --edge
```

Install the locally built artifact and connect its interfaces:

```bash
sudo snap install --dangerous ./simple-ethercat-driver-ros2_0.1_amd64.snap

sudo snap connect \
  simple-ethercat-driver-ros2:ros-lyrical-ros-base \
  ros-lyrical-ros-base:ros-lyrical-ros-base

sudo snap connect \
  simple-ethercat-driver-ros2:ethercat-master \
  simple-ethercat-driver-ros2:ethercat-master-slot
```

`--dangerous` is required for an unsigned local artifact. It does not change
the snap's strict confinement.

Verify all connections:

```bash
snap connections simple-ethercat-driver-ros2
```

The self-provided `custom-device` slot makes local strict-confinement testing
possible. Store publication and auto-connection require review because
`custom-device` is super-privileged.

The host must already have the IgH master and NIC driver loaded, expose
`/dev/EtherCAT0`, and use the validated EasyCAT receive timeout of 5000 µs.

## Basic terminal demo

Connect and power the EasyCAT device, then run:

```bash
snap run simple-ethercat-driver-ros2.demo
```

Wait for the dashboard status to change from `WAITING FOR ETHERCAT DATA` to
`LIVE`. Rotate the two dials on the top-mounted EasyCAT Test shield; `A0` and
`A1` should change independently from 0 to 255. Stop the demo with Ctrl-C.

## ROS 2 topic and visualization

The demo publishes `sensor_msgs/msg/JointState` on `/joint_states` with a fixed
order:

1. `easycat_analog_0` → `position[0]`
2. `easycat_analog_1` → `position[1]`

In another terminal, inspect the data or publication rate with:

```bash
snap run simple-ethercat-driver-ros2.ros2 topic echo /joint_states
snap run simple-ethercat-driver-ros2.ros2 topic hz /joint_states
```

For the recorded visualization demo:

1. Start `snap run simple-ethercat-driver-ros2.demo` in a terminal.
2. Start PlotJuggler with ROS 2 streaming on domain 0.
3. Plot `/joint_states/position[0]` and `/joint_states/position[1]` and label
   them A0 and A1.
4. Place the terminal, PlotJuggler, and a webcam view of the EasyCAT board on
   one screen.
5. Record the screen while rotating the two potentiometers.

Both applications use normal ROS 2 DDS networking, so no bridge process is
required between the snap and a host PlotJuggler installation.

## Troubleshooting

### Verify packaged CLI and slave discovery

With the host master running and exposing `/dev/EtherCAT0`:

```bash
snap run simple-ethercat-driver-ros2.ethercat version
snap run simple-ethercat-driver-ros2.ethercat slaves
snap run simple-ethercat-driver-ros2.ros2 pkg prefix ethercat_driver
snap run simple-ethercat-driver-ros2.ros2 pkg prefix ethercat_generic_slave
```

The expected slave identity is `Generic 32+32 bytes rev 1`.

### Dashboard reports `BRIDGE STOPPED` or `NO DATA`

If the dashboard reports `BRIDGE STOPPED` or `NO DATA`, inspect the demo log
above and check:

```bash
snap connections simple-ethercat-driver-ros2
snap run simple-ethercat-driver-ros2.ethercat slaves
tail -n 200 ~/snap/simple-ethercat-driver-ros2/current/easycat-demo.log
```

## Available snap applications

| Application | Command | Purpose |
|---|---|---|
| Demo | `snap run simple-ethercat-driver-ros2.demo` | Start the bridge and live dashboard |
| Bridge | `snap run simple-ethercat-driver-ros2.bridge` | Start the ROS stack without the dashboard |
| EtherCAT CLI | `snap run simple-ethercat-driver-ros2.ethercat` | Inspect the host master and slaves |
| ROS CLI | `snap run simple-ethercat-driver-ros2.ros2` | Inspect ROS nodes, topics, and packages |
| SDO server | `snap run simple-ethercat-driver-ros2.sdo-server` | Start the packaged ICube SDO service executable |

The tested EasyCAT firmware has no mailbox protocol, so SDO upload/download is
not part of this demonstration even though the generic server executable is
packaged.

## Repository layout

```text
.
├── snap/
│   ├── snapcraft.yaml
│   └── local/
│       ├── ament_target_dependencies.cmake
│       ├── lyrical-ament-target-dependencies.patch
│       └── easycat_bridge/
│           ├── config/          # PDO and controller configuration
│           ├── easycat_bridge/  # dashboard and topic adapter
│           └── launch/          # ROS 2 Control launch
├── demo-steps.md                # complete presentation runbook
├── reproducibility-guide.md     # reproducible build and validation guide
└── summary.md                   # concise project summary
```

## Validation evidence

The renamed Snapcraft project builds cleanly in LXD. Inspection of the packed
metadata confirms the `simple-ethercat-driver-ros2` name, five applications,
strict confinement, ROS content interface, and EtherCAT `custom-device`
interface.

The physical and synthetic validation below used the pre-rename artifact built
from the same functional source. It was 192,126,976 bytes (183 MiB) with
SHA-256:

```text
22e4a06788f9813c1ebebaf79757d0e8c790a69c1b52dd9f0105bae731b9a8e0
```

Installation and synthetic ROS checks were completed in a clean Ubuntu 26.04
LXD VM:

- Snapcraft produced the amd64 artifact successfully.
- The strict snap installed successfully.
- The ROS content and custom EtherCAT interfaces connected successfully.
- The bundled CLI reported IgH 1.6.9.
- ROS discovered `easycat_bridge`, `ethercat_driver`, and
  `joint_state_broadcaster`.
- The packaged launch description parsed successfully.
- The complete EasyCAT PDO configuration loaded into the ICube driver.
- A synthetic dynamic-state input containing A0=42 and A1=211 produced:

```yaml
name:
  - easycat_analog_0
  - easycat_analog_1
position:
  - 42.0
  - 211.0
```

Physical validation was then completed on Ubuntu 26.04 with the EtherCAT NIC
passed through to the test VM. Ubuntu supplied the `ec_master` and `ec_generic`
kernel modules and `/dev/EtherCAT0`; the snap supplied the IgH CLI and library,
ICube driver, ROS 2 integration, configuration, and applications. Validation
confirmed:

- the confined CLI discovered `Generic 32+32 bytes rev 1`;
- the bridge moved the slave from PREOP to OP;
- the 64-byte process domain reported WorkingCounter 3/3;
- the terminal dashboard reached `LIVE` and both A0 and A1 responded to their
  physical dials;
- `/joint_states` published `easycat_analog_0` and `easycat_analog_1` with live
  values; and
- a host PlotJuggler instance received and plotted both values over ROS 2 DDS.

The Arduino used the extended firmware from
`canonical/ethercat-easycat-testing-repo` commit
`67e36f641bf90a472ac88ed1969bbfa6cc2792c6`
(`sketch_jul2b/TestEasyCAT.ino`). That separate repository already contains the
required A0/A1 process-data extension; the firmware is not duplicated here.

This completes the physical-device acceptance test for the userspace snap.

## Known limitations

- The EasyCAT-specific mapping assumes the exact 32+32-byte process image
  documented above.
- This is a userspace snap; it cannot configure, load, or replace host kernel
  modules.
- `custom-device` requires Snap Store review for publication or automatic
  connection.
- The ROS 2 Lyrical Snapcraft extension and content snap currently use the
  experimental/edge delivery path.
- The tested EasyCAT firmware exposes PDO data but no CoE mailbox or SDO object
  dictionary.

## Licensing

The local EasyCAT ROS package declares Apache-2.0. The snap also packages IgH
EtherCAT GPL-2.0+ components. See the source projects and package metadata for
their applicable license terms.
