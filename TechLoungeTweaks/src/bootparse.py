"""Turn the boot optimiser's raw PowerShell output into UI-friendly events."""

import re

WHATIF = re.compile(
    r'What if:\s*Performing the operation "(?P<op>[^"]*)"\s*'
    r'on target "(?P<target>[^"]*)"')
SECTION = re.compile(r"^\s*===\s*(?P<name>.+?)\s*===\s*$")
TAGGED = re.compile(r"^\s*\[(?P<tag>OK|SKIP|INFO|WARN|FAIL)\]\s*(?P<text>.*)$")

# Registry value name -> what a human calls it
FRIENDLY = {
    "HiberbootEnabled": ("Fast Startup", "on"),
    "WaitToKillServiceTimeout": ("Service shutdown timeout", "2 seconds"),
    "WaitToKillAppTimeout": ("App shutdown timeout", "3 seconds"),
    "HungAppTimeout": ("Hung app detection", "3 seconds"),
    "SyncForegroundPolicy": ("Logon network wait", "off"),
    "DelayedDesktopSwitchTimeout": ("Delayed desktop switch", "removed"),
    "StartupDelayInMSec": ("Startup app delay", "removed"),
    "MenuShowDelay": ("Menu animation delay", "20 ms"),
    "DelayedAutostart": ("Service start", "delayed"),
    "Start": ("Service startup type", "changed"),
}

NOISE = (
    "CategoryInfo", "FullyQualifiedErrorId", "At line:", "+ ",
    "~~~", "Check \nthe spelling", "the spelling of the name",
)


def _friendly_target(target, op):
    """Turn a registry path + operation into 'Setting -> value'."""
    target = (target or "").rstrip("\\")
    leaf = target.split("\\")[-1] if target else ""
    label, default_val = FRIENDLY.get(leaf, (leaf or target, None))

    val = None
    m = re.match(r"Set to\s*(.*)", op or "")
    if m:
        raw_val = m.group(1).strip()
        # "Fast Startup -> 1" means nothing; use the human wording when we
        # have one and the value is just a bare number.
        if default_val and (not raw_val or raw_val.isdigit()):
            val = default_val
        else:
            val = raw_val or default_val
    elif op:
        val = op.strip()

    if not label:
        label = target
    return label, (val or "")


def parse_line(line):
    """Return (kind, text, detail) or None if the line is noise.

    kind: step | ok | skip | info | warn | fail | plan | banner
    """
    raw = line.rstrip("\n\r")
    if not raw.strip():
        return None

    m = SECTION.match(raw)
    if m:
        return ("step", m.group("name"), "")

    m = TAGGED.match(raw)
    if m:
        tag = m.group("tag").lower()
        kind = {"ok": "ok", "skip": "skip", "info": "info",
                "warn": "warn", "fail": "fail"}[tag]
        return (kind, m.group("text").strip(), "")

    m = WHATIF.search(raw)
    if m:
        label, val = _friendly_target(m.group("target"), m.group("op"))
        return ("plan", label, val)

    stripped = raw.strip()
    if stripped.startswith(("+---", "|", "---")):
        return None
    if any(n in raw for n in NOISE):
        return None
    if re.match(r"^\S+\s*:\s*The term", stripped):
        return ("fail", stripped.split(":")[0].strip() + " failed", "")
    if "Invalid class" in stripped or stripped.endswith("Exception"):
        return ("fail", stripped[:90], "")
    if stripped.startswith("At "):
        return None
    return ("info", stripped, "")


READONLY_SECTIONS = {
    "hardware detection",
    "anti-cheat prerequisites (read-only)",
}

# Individual lines that describe a finding even outside a read-only section.
INFO_PATTERNS = (
    "secure boot", "tpm", "vbs:", "no dual-boot", "hypervisorlaunchtype",
    "already", "not auto-start", "not present",
)


def is_finding(text, section):
    """True when an [OK] line is reporting state rather than changing it."""
    if (section or "").strip().lower() in READONLY_SECTIONS:
        return True
    low = text.lower()
    return any(p in low for p in INFO_PATTERNS)


def summarise(events):
    """Group parsed events into the three lists the results view shows."""
    planned, done, skipped, attention, findings = [], [], [], [], []
    for ev in events:
        kind, text, detail = ev[0], ev[1], ev[2]
        section = ev[3] if len(ev) > 3 else ""
        if kind == "plan":
            planned.append((text, detail))
        elif kind == "ok":
            # An [OK] in a read-only section is a status report, not a change -
            # listing those under "Changed" claimed edits that never happened.
            (findings if is_finding(text, section) else done).append((text, ""))
        elif kind == "skip":
            skipped.append((text, ""))
        elif kind in ("warn", "fail"):
            attention.append((text, ""))
    return planned, done, skipped, attention, findings
