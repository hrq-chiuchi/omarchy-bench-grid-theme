import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

// Bench Grid: stay-awake as the mockup's mode mark, a 7px dot. Amber while the system stays awake;
// otherwise hidden, and a hollow ring while the bar's indicator peek is open, so it can be switched
// on the way the stock indicator can. Replaces StayAwake in omarchy.indicators (drop it from that
// entry's "items"). Third-party widgets get no first-party services, so the state comes from the file
// the idle service itself watches, and the toggle goes through `omarchy toggle idle`.
BarWidget {
  id: root

  readonly property string stateDir: Quickshell.env("HOME") + "/.local/state/omarchy/indicators"
  property bool stayAwake: false
  // In the right section it shows on the right-section peek (the one that opens the tray drawer,
  // from the Bench Grid bar patch); elsewhere on the left-side indicator peek.
  readonly property bool inRightSection: fixedEdge === "end"
  readonly property bool peekOpen: !!bar && (inRightSection
    ? bar.rightSectionRevealHeld === true
    : bar.centerSectionRevealHeld === true && bar._centerHoverRevealSuppressed !== true)

  // "alwaysShow": true in its bar entry keeps the ring showing when off (for the tray drawer, which
  // has no indicator peek of its own), as omarchy.indicators' own alwaysShow does.
  readonly property bool alwaysShow: !!settings && settings.alwaysShow === true
  // Placement, from its bar entry: "slot" (px along the bar, default the status slot) and "offset" (px the
  // dot moves from the slot's centre; negative toward the start). Tucked after the clock: slot 10, offset -3
  // pulls the dot against the clock's own padding.
  readonly property real slotLength: settings && isFinite(Number(settings.slot)) && Number(settings.slot) > 0 ? Number(settings.slot) : Style.bar.statusSlot
  readonly property real dotOffset: settings && isFinite(Number(settings.offset)) ? Number(settings.offset) : 0

  // Bar.qml collapses the slot of an invisible widget, so off and unpeeked takes no room.
  visible: stayAwake || peekOpen || alwaysShow
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  Translations { id: strings; directory: Qt.resolvedUrl("i18n") }

  function refresh() {
    if (!probe.running) probe.running = true
  }

  function toggle() {
    root.stayAwake = !root.stayAwake
    if (root.bar) root.bar.run("omarchy toggle idle toggle")
  }

  Process {
    id: probe
    command: ["test", "-f", root.stateDir + "/stay-awake"]
    onExited: function(exitCode) {
      root.stayAwake = exitCode === 0
      dirWatch.reload()
    }
  }

  // The service deletes and recreates the file, so watch its directory, as the service does.
  FileView {
    id: dirWatch
    path: root.stateDir
    watchChanges: true
    printErrors: false
    onFileChanged: root.refresh()
  }

  // Fallback if the directory did not exist yet when the watch was set up.
  Timer {
    interval: 15000
    running: true
    repeat: true
    onTriggered: root.refresh()
  }

  Component.onCompleted: refresh()

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    // A blank glyph keeps the button counted as having content; the dot is drawn below at its own
    // size (an iconComponent would be scaled up to the full icon size).
    text: " "
    tooltipText: root.stayAwake ? strings.t("tooltip.allowIdle") : strings.t("tooltip.stayAwake")
    dimmed: !root.stayAwake
    horizontalMargin: 5
    verticalPadding: 5
    fixedWidth: root.vertical ? -1 : root.slotLength
    fixedHeight: root.vertical ? root.slotLength : -1
    onPressed: function(buttonCode) {
      if (buttonCode === undefined || buttonCode === Qt.LeftButton) root.toggle()
    }

    Rectangle {
      readonly property real dotSize: 7
      width: dotSize
      height: dotSize
      radius: dotSize / 2
      x: Math.round((button.width - width) / 2 + (root.vertical ? 0 : root.dotOffset))
      y: Math.round((button.height - height) / 2 + (root.vertical ? root.dotOffset : 0))
      scale: button.pressScale
      color: root.stayAwake ? button.activeColor : "transparent"
      border.width: root.stayAwake ? 0 : 1
      border.color: button.foreground
    }
  }
}
