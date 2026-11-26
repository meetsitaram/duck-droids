#!/bin/bash
# Two network settings for the duck's Pi Zero 2 W (2026-11-25). setup_pi.sh runs this; safe to run again.
#   1. Wi-Fi power saving off. With it on (NetworkManager's default), the Pi dropped its own Wi-Fi link every couple of minutes
#      ("CTRL-EVENT-DISCONNECTED reason=0 locally_generated=1" in journalctl -u wpa_supplicant) and came back on a new address, killing
#      every ssh and copy; the one radio chip also carries the Bluetooth speaker and controller.
#   2. A network link over USB, for when the Wi-Fi is gone: a plain micro-USB cable from the PC to the Pi's DATA port (the middle one,
#      marked USB; the corner one, PWR IN, carries no data) and the Pi shows up on the PC as a USB network adapter, CDC NCM, which
#      Windows 10/11 and Linux drive with their own drivers (the first try, g_ether, came up on Windows as a serial port, COM5, and the
#      kernel has no g_ncm, so the gadget is built in configfs at every boot by the duck-usb-gadget service). The Pi is 10.42.0.1 on
#      that link and hands the PC an address: ssh USER@10.42.0.1. The port runs as OTG (dwc2): host for the servo bus board, as
#      before, when that board's cable is in, a USB device when a PC is. One data port: the servo board or the PC, not both at once.
#      If the servo board stops showing up with its cable in (ls /dev/ttyACM* /dev/ttyUSB*): sudo bash net_setup.sh usb-off.
#   sudo bash net_setup.sh             install both (the Wi-Fi change and the cmdline need a reboot to be certain)
#   sudo bash net_setup.sh usb-off     the USB link off (the port host-only again, as Raspberry Pi OS ships it)
#   sudo bash net_setup.sh remove      both off
set -e
[ "$(id -u)" = 0 ] || { echo 'run with sudo'; exit 1; }
CFG=/boot/firmware/config.txt
CMD=/boot/firmware/cmdline.txt
PS=/etc/NetworkManager/conf.d/duck-wifi-powersave.conf
OVL='dtoverlay=dwc2,dr_mode=otg'
BIN=/usr/local/sbin/duck-net-setup.sh
UNIT=/etc/systemd/system/duck-usb-gadget.service
G=/sys/kernel/config/usb_gadget/duck

gadget_up() {             # the NCM gadget in configfs, bound to the port; usb0 appears
  modprobe libcomposite
  [ -d $G ] && [ -n "$(cat $G/UDC 2>/dev/null)" ] && return 0
  mkdir -p $G && cd $G
  echo 0x1d6b > idVendor; echo 0x0104 > idProduct; echo 0x0100 > bcdDevice; echo 0x0200 > bcdUSB
  echo 0xEF > bDeviceClass; echo 0x02 > bDeviceSubClass; echo 0x01 > bDeviceProtocol   # composite with an IAD: Windows' usbccgp, then UsbNcm
  mkdir -p strings/0x409 configs/c.1/strings/0x409 functions/ncm.usb0
  echo "duck-$(cat /etc/machine-id | head -c 8)" > strings/0x409/serialnumber
  echo 'duck-droids' > strings/0x409/manufacturer
  echo 'duck USB network' > strings/0x409/product
  echo 'NCM' > configs/c.1/strings/0x409/configuration
  echo 250 > configs/c.1/MaxPower
  echo 02:dd:00:00:00:01 > functions/ncm.usb0/dev_addr      # fixed MACs: the same adapter on the PC every time
  echo 02:dd:00:00:00:02 > functions/ncm.usb0/host_addr
  [ -e configs/c.1/ncm.usb0 ] || ln -s functions/ncm.usb0 configs/c.1/
  ls /sys/class/udc | head -1 > UDC
}

usb_off() {
  systemctl disable --now duck-usb-gadget.service 2>/dev/null || true
  rm -f $UNIT; systemctl daemon-reload
  sed -i "/^# the USB data port as OTG/d; /^$OVL\$/d" $CFG
  sed -i -E '1 s/ modules-load=[^ ]*//g' $CMD
  nmcli connection delete duck-usb >/dev/null 2>&1 || true
}

case "${1:-install}" in
install)
  printf '[connection]\n# 2 = off. On, the Pi Zero 2 W dropped its own Wi-Fi link every couple of minutes (pi/net_setup.sh)\nwifi.powersave = 2\n' > $PS
  [ -f $CFG.before-net-setup ] || cp $CFG $CFG.before-net-setup
  [ -f $CMD.before-net-setup ] || cp $CMD $CMD.before-net-setup
  # its own [all] at the end, so it can't land under a [cm4] / [cm5] / [pi5] section (Raspberry Pi OS has a dr_mode=host under [cm5])
  grep -qx "$OVL" $CFG || printf '\n[all]\n# the USB data port as OTG: host for the servo board, a USB network device to a PC (pi/net_setup.sh)\n%s\n' "$OVL" >> $CFG
  sed -i -E '1 s/ modules-load=[^ ]*//g; 1 s/$/ modules-load=dwc2/' $CMD     # the driver only; any earlier g_ether / g_ncm gone
  cp "$0" $BIN; chmod 755 $BIN
  printf '[Unit]\nDescription=Duck: the USB network gadget (CDC NCM) on the data port (pi/net_setup.sh)\nAfter=sys-kernel-config.mount\n\n[Service]\nType=oneshot\nRemainAfterExit=yes\nExecStart=/bin/bash %s gadget\n\n[Install]\nWantedBy=multi-user.target\n' $BIN > $UNIT
  systemctl daemon-reload; systemctl enable duck-usb-gadget.service >/dev/null 2>&1
  nmcli connection delete duck-usb >/dev/null 2>&1 || true
  # priority: the image's catch-all wired profile (netplan-eth0, from network-config) took usb0 first and waited there for a DHCP address
  nmcli connection add type ethernet ifname usb0 con-name duck-usb autoconnect yes connection.autoconnect-priority 100 \
    ipv4.method shared ipv4.addresses 10.42.0.1/24 ipv6.method link-local >/dev/null
  modprobe -r g_ether 2>/dev/null || true
  if [ -n "$(ls /sys/class/udc 2>/dev/null)" ]; then systemctl restart duck-usb-gadget.service && sleep 2 && nmcli connection up duck-usb >/dev/null 2>&1 || true; fi
  echo 'installed: Wi-Fi power saving off, the USB link on (reboot to be certain of both).'
  ;;
gadget)                   # the service, at every boot
  gadget_up
  ;;
usb-off)
  usb_off
  echo 'USB link off. Reboot.'
  ;;
remove)
  rm -f $PS
  usb_off
  echo 'both off. Reboot.'
  ;;
*) sed -n '2,17p' "$0"; exit 1 ;;
esac
