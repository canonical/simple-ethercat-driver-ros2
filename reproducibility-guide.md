# Reproducibility Guide

This guide records the pinned sources, packaging steps, installation
prerequisites, and validation needed to reproduce the EtherCAT userspace and
ROS 2 bridge snap. It intentionally excludes the detailed debugging history.
Update it as the build, installation, and hardware validation progress.

## Objective

Provide an installable Ubuntu 26.04 snap containing the EtherCAT userspace and
ROS 2 bridge while using the IgH EtherCAT master kernel modules supplied by the
host operating system.

The target result is:

1. Install the snap on Ubuntu 26.04.
2. Use the host's `ec_master` and NIC-specific EtherCAT kernel modules.
3. Access the host-created `/dev/EtherCAT*` device from the confined snap.
4. Run the bundled IgH CLI and ROS 2 EtherCAT driver.
5. Publish EasyCAT process data through ROS 2 `/joint_states`.

## Source components and versions

| Component | Source/version | Purpose |
|---|---|---|
| Snap base | `core26` | Ubuntu 26.04 runtime |
| ROS 2 | Lyrical Luth | Target ROS 2 release for Ubuntu 26.04 |
| ROS Snapcraft extension | `ros2-lyrical-ros-base` | ROS runtime setup and content-snap integration |
| IgH EtherCAT | `stable-1.6` commit `beb2bf07df4a19024490c0517137cffa8f97ace0` (1.6.9) | EtherCAT userspace API, shared library, and CLI |
| ICube ROS 2 EtherCAT driver | `jazzy` commit `7a32bd7b8fc066c6668b1df7446c89aff570bb7d` | ROS 2 Control EtherCAT hardware integration |
| ROS 2 Control | Lyrical Debian packages | Controller manager and hardware interface runtime |
| Joint State Broadcaster | Lyrical Debian package | Publishes hardware state as `/joint_states` |
| Robot State Publisher | Lyrical Debian package | Supplies the hardware description to controller manager |
| Xacro | Lyrical Debian package | Expands the robot and hardware description |

The source revisions are pinned in `snap/snapcraft.yaml` so builds do not
silently change when an upstream branch advances.

## Engineering steps completed

### 1. Created the Snapcraft project

The `snap/snapcraft.yaml` recipe and project README were created under
`simple-ethercat-driver-ros2`.

The recipe currently defines a strict `core26` snap named
`simple-ethercat-driver-ros2` and uses the experimental ROS 2 Lyrical
extension.

### 2. Packaged IgH userspace without kernel modules

An `ethercat-userspace` part was added to build IgH from the pinned source.
It is configured with:

- `--prefix=/usr/local/etherlab`
- `--disable-kernel`
- `--disable-eoe`
- `--disable-initd`

This packages the userspace API and tools without attempting to compile,
install, or manage kernel modules from inside the snap. The important packaged
artifacts are:

- `ecrt.h`
- `libethercat.so`
- the `ethercat` command-line application

The `/usr/local/etherlab` prefix also matches a path already supported by the
ICube driver's CMake discovery logic.

### 3. Packaged the ROS 2 EtherCAT driver

An `ethercat-driver` colcon part was added for the pinned ICube source. It is
built after the IgH userspace part so the EtherCAT headers and shared library
are available first.

The CMake arguments explicitly select the staged IgH artifacts:

- `ETHERCAT_INCLUDE_DIR` points to the bundled EtherLab include directory.
- `ETHERCAT_LIB` points to the bundled `libethercat.so`.
- `BUILD_TESTING` is disabled for the production package build.

This removes any build-time dependency on a host installation under
`/usr/local` and ensures that the ROS driver links to the userspace library
provided by the snap.

### 4. Added ROS 2 runtime components

The recipe adds the Lyrical packages required beyond the ROS base content snap:

- `ros-lyrical-ros2-control`
- `ros-lyrical-controller-manager`
- `ros-lyrical-joint-state-broadcaster`
- `ros-lyrical-robot-state-publisher`
- `ros-lyrical-xacro`

The ROS applications receive an `LD_LIBRARY_PATH` containing the snap's
EtherLab library directory so `libethercat.so` can be resolved at runtime
without changing the host's dynamic linker configuration.

### 5. Defined packaged applications

The recipe currently exposes these applications:

| Application | Packaged command | Purpose |
|---|---|---|
| `ethercat` | IgH `ethercat` CLI | Inspect the master, slaves, domains, and process data |
| `ros2` | ROS 2 CLI | Inspect packages, nodes, topics, and services inside the snap environment |
| `sdo-server` | ICube `ethercat_sdo_srv_server` | Expose the driver's SDO service executable when the slave supports mailbox protocols |
| `bridge` | EasyCAT ROS launch | Start the ROS 2 Control bridge, broadcaster, and topic adapter |
| `demo` | EasyCAT terminal monitor | Start the bridge and display live A0/A1 values while publishing `/joint_states` |

The EasyCAT firmware currently used for validation has no mailbox protocol, so
the SDO server is packaged but is not part of the EasyCAT PDO validation path.

### 6. Added confined EtherCAT device access

A `custom-device` interface named `ethercat-master` was added for
`/dev/EtherCAT[0-9]*`. A matching local slot is included so the interface can
be connected during development installation.

This interface was selected instead of `system-files` because access to a
device node requires both filesystem permission and device-cgroup permission.
The interface is super-privileged, so Store publication and automatic
connection will require Snap Store review.

### 7. Validated the expanded recipe

Snapcraft successfully expands the recipe when experimental extensions are
enabled. This confirms that the `core26` base, Lyrical extension, parts,
applications, and interface declarations are accepted by the current
Snapcraft release.

### 8. Added ROS 2 Lyrical CMake compatibility

The pinned ICube Jazzy source uses the legacy `ament_target_dependencies`
function. ROS 2 Lyrical retains a package with that name but has removed the
function in favor of modern CMake targets.

A source patch was added under `snap/local` and is applied during the driver's
pull step. It explicitly loads the remaining helper package in each ICube
package that uses the command. An Apache-2.0 compatibility copy of the Jazzy
function was also added and is injected into every colcon CMake project. The
corresponding Lyrical package is an explicit build dependency. Keeping these as
separate compatibility files preserves the pinned upstream source while making
the Lyrical-specific code changes reviewable.

### 9. Added the EasyCAT process-data configuration

The `easycat_bridge` package contains the complete process image expected by the
AB&T EasyCAT standard 32+32-byte firmware:

- vendor ID `0x0000079a`
- product ID `0x00defede`
- RxPDO `0x1600`, with all 32 byte entries at object `0x0005`
- TxPDO `0x1a00`, with all 32 byte entries at object `0x0006`
- SM0 configured for output/RxPDO with watchdog enabled
- SM1 configured for input/TxPDO with watchdog disabled
- no mailbox SDO configuration and no Distributed Clock activation

Every byte is declared because IgH must register the complete slave process
layout. TxPDO bytes 0 and 1 are exposed as `analog_input_0` and
`analog_input_1`; the remaining bytes preserve layout without creating ROS
interfaces. Unused output bytes receive a safe default of zero.

### 10. Added ROS 2 Control and `/joint_states` integration

The ROS hardware description creates one GPIO resource named `easycat` using
the ICube `GenericEcSlave` at alias 0, position 0. A joint-state broadcaster
publishes its two custom interfaces on the dynamic state topic.

A small adapter converts that resource into a standard
`sensor_msgs/msg/JointState` message with two ordered entries:

1. `easycat_analog_0`
2. `easycat_analog_1`

This adapter is necessary because one physical GenericEcSlave module belongs to
one ROS 2 Control resource, while the required public message represents A0 and
A1 as separate joint values.

### 11. Added the presentation application

The `demo` snap application starts the full bridge in a background process and
renders `/joint_states` as a fixed live terminal dashboard. It displays A0 and
A1 numerically and as 0–255 bar graphs. ROS launch output is redirected to
`easycat-demo.log` under the snap's user-data directory, keeping the recorded
terminal uncluttered.

Fast DDS is configured to use UDPv4 for packaged ROS applications. This avoids
attempted shared-memory transport setup under strict snap confinement while
retaining communication with ROS 2 visualization tools on the host.

### 12. Resolved multi-part colcon staging

The ICube driver and local EasyCAT package are separate colcon parts. Both
generate merged-prefix root setup scripts, which initially collided during
Snapcraft staging. The EasyCAT part now filters only those duplicate root setup
files; its package index, Python modules, executables, launch files, and
environment hooks remain staged. This keeps local source changes tracked by
Snapcraft while producing one coherent ROS overlay.

### 13. Built and inspected the installable artifact

Before the package rename, Snapcraft produced a 192,126,976-byte (183 MiB)
amd64 artifact on July 20, 2026. It contains:

- IgH 1.6.9 userspace CLI, headers, and `libethercat.so.1`
- all pinned ICube driver libraries and plugin metadata
- ROS 2 Control, controller manager, joint-state broadcaster, and robot-state
  publisher runtime
- the EasyCAT YAML, launch files, adapter, and terminal monitor
- strict `custom-device`, network, and network-bind metadata

ELF inspection confirmed that `libethercat_interface.so` depends on the bundled
`libethercat.so.1`. The snap applications add the bundled EtherLab directory to
their runtime library path.

### 14. Validated installation and ROS data conversion

The artifact was installed as a strict snap in a clean Ubuntu 26.04 LXD virtual
machine. The ROS content interface and local EtherCAT custom-device interface
were connected. Validation confirmed:

- the packaged CLI reports IgH 1.6.9 at the pinned revision
- ROS discovers `easycat_bridge`, `ethercat_driver`, and
  `joint_state_broadcaster` inside the snap
- the packaged EasyCAT bridge launch description parses successfully
- the packaged demo application starts and displays the expected terminal
  dashboard
- UDP-only Fast DDS removes the shared-memory confinement errors
- a synthetic EasyCAT dynamic-state message with A0=42 and A1=211 produces
  `/joint_states` names `easycat_analog_0`, `easycat_analog_1` and positions
  42.0, 211.0

The VM intentionally has no `/dev/EtherCAT0`, so failure to activate the master
there is expected and separate from the final physical-device validation.

### 15. Completed physical-device validation

The same strict snap artifact was validated with the physical EasyCAT slave on
July 21, 2026. The test used an Ubuntu 26.04 libvirt VM with the ASIX EtherCAT
NIC passed through. Ubuntu supplied the `ec_master` and `ec_generic` kernel
modules and created `/dev/EtherCAT0`; no kernel component came from the snap.

The Arduino ran the extended validation firmware from
`canonical/ethercat-easycat-testing-repo` commit
`67e36f641bf90a472ac88ed1969bbfa6cc2792c6`
(`sketch_jul2b/TestEasyCAT.ino`). That firmware publishes A0 and A1 in the first
two bytes of the 32-byte TxPDO and supplies the additional deterministic test
signals used during hardware bring-up. The firmware source remains in the
separate testing repository and was already committed before this snap work.

The tested artifact was:

- size: 192,126,976 bytes (approximately 192 MB / 183 MiB)
- SHA-256: `22e4a06788f9813c1ebebaf79757d0e8c790a69c1b52dd9f0105bae731b9a8e0`

The ROS content and EtherCAT `custom-device` interfaces were connected before
testing. The physical test confirmed:

- the bundled CLI discovered `Generic 32+32 bytes rev 1`
- the slave entered OP while the packaged bridge was active
- the 64-byte EtherCAT domain reported WorkingCounter 3/3
- the packaged demo application reached `LIVE`
- both physical dials independently changed the dashboard's A0 and A1 values
- `/joint_states` published `easycat_analog_0` and `easycat_analog_1` with the
  live physical values
- PlotJuggler on the host discovered `/joint_states` over ROS 2 DDS and plotted
  both channels

Artifact inspection also confirmed that the tested snap contains the final
controller parameters and passes the controller YAML to the ROS 2 Control
spawner. The committed functional configuration therefore matches the runtime
behavior exercised by the physical test; subsequent source changes only polish
user-visible naming and documentation.

## Host-side prerequisite established

Ubuntu supplies the version-compatible IgH kernel modules. The host must load
and bind them to the EtherCAT NIC so `/dev/EtherCAT0` exists before the snap is
started.

Hardware validation also established that this EasyCAT board behind the ASIX
USB NIC needs IgH's global datagram receive timeout set to 5000 microseconds in
the kernel-side master. This is a host kernel-module requirement and is not a
change to the userspace bundled by this snap.

## Current status

- The 183 MiB installable snap builds successfully.
- IgH userspace, the ICube driver, and all required ROS components are packaged.
- Strict installation, interface connection, CLI execution, package discovery,
  and launch parsing are validated on Ubuntu 26.04.
- The EasyCAT 32+32-byte PDO and SM0/SM1 configuration is packaged.
- The one-command terminal demo and `/joint_states` conversion are packaged.
- The ROS conversion path is validated with synthetic A0/A1 data.
- The physical slave, complete process domain, live dashboard, `/joint_states`,
  and PlotJuggler path are validated through the strict snap.

## Acceptance result

ROBENG-1886's engineering objective is complete: all required EtherCAT
userspace components are packaged in the snap, the Ubuntu 26.04 kernel modules
remain external, and the resulting snap has been exercised end to end with the
physical EtherCAT device. Store review for automatic `custom-device` connection
is a publication step, not an outstanding functional validation item.
