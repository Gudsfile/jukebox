# Readers

A reader is an outbound adapter that detects NFC tags and returns their UID to the jukebox.

Select a reader with `--reader`:

```shell
jukebox --player PLAYER --reader READER
```

You can also persist the choice so you don't need to pass it each time:

```shell
jukebox-admin settings set jukebox.reader.type READER
```

> [!TIP]
> Tag UIDs are returned in colon-separated hex format: `xx:xx:xx:xx`.

Available readers:

- [Dry Run](#dry-run-dryrun)
- [Pn532 NFC](#pn532-nfc-pn532)

## Dry Run (`dryrun`)

Simulates NFC tag reading via stdin. Useful for development when no NFC hardware is available.

Input format: `tag_id` or `tag_id duration_seconds`

- `tag_id`: full identifier of the tag in the system's colon-separated hex format
- `duration_seconds`: non-negative float; how long the tag stays in place before being removed (default: `immediate`)

Example: `your:tag:uid 2.5`

No configuration required.

### Persistent settings

| Settings path | Description | Value |
| --- | --- | --- | 
| `jukebox.reader.type` | Persists the reader choice across restarts | dryrun |

## Pn532 NFC (`pn532`)

Reads physical NFC tags using a PN532 reader.

### Supported hardware

- NFC reader: **PN532** (e.g. [Waveshare PN532 NFC HAT](https://www.waveshare.com/wiki/PN532_NFC_HAT))
- NFC tags: **NTAG2xx**

### Installation

The `pn532` extra is required:

```shell
pip install "gukebox[pn532]"
```

> [!IMPORTANT]
> On Python 3.13+, use the **system Python** and install `python3-lgpio` from your OS package manager before creating your virtual environment:
> ```shell
> sudo apt update && sudo apt install python3-lgpio
> python3 -m venv --system-site-packages jukebox
> source jukebox/bin/activate
> pip install "gukebox[pn532]"
> ```
> A separately installed Python 3.13+ (from `uv`, `pyenv`, Homebrew, etc.) may not be able to import the system `lgpio` package even with `--system-site-packages`. Use the system Python or Python 3.12 or lower instead.

### Hardware setup

Enable the SPI interface on the Raspberry Pi:

```shell
sudo raspi-config
# Interface Options > SPI > Enable > Yes
```

### Persistent settings

| Settings path | Description | Value |
| --- | --- | --- |
| `jukebox.reader.type` | Persists the reader choice across restarts | `pn532` |
| `jukebox.reader.pn532.read_timeout_seconds` | Timeout in seconds for each NFC poll attempt (must be > 0) | `0.1` |
