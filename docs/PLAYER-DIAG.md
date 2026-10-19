# Experimental resume / repeated-arrow-seek build

Based on SMB review head 73ea6de942394d3f0e03139e7ab0dc0be9935737.
This is a separate experiment, not a change to upstream SMB PR #28.

Changes:

- Saved resume first decodes initial video frames, then uses the arrow-seek
  preparation path with a fixed target and no interactive preview loop.
  A brief flash of the beginning is expected. This lets AVI MPEG-4 consume
  initial in-band codec headers before seeking away from them.
- After preview, seek through the container again instead of rewinding only
  the file position. This resets demuxer stream counters as well as file bytes.
- Check the return of the repeated container seek and of the refill.
- Immutable Pxx diagnostic overlays are selected by the video renderer.
  No filesystem logging, network logging, watchdog or forced IOP reset added.

Pxx codes (photograph/film the last visible code during failure):

| Code | Main-thread stage |
|---|---|
| P00 | button/main loop |
| P10 | IPU synchronization before stopping workers |
| P11 | terminating video/decode workers |
| P12 | waiting for audio renderer to stop |
| P13 | draining/resetting queues |
| P21 | configuring preview stream |
| P22 | decoding preview |
| P23 | waiting for accepted preview display |
| P24 | resetting after preview |
| P25 | restoring container position and stream counters |
| P30 | audio decoder reinitialization |
| P31 | starting worker threads |
| P32 | prebuffering packets |
| P40 | container ReadPacket (including possible buffer/network wait) |
| P41 | posting a packet |

The overlay uses the existing video-render path. If that path stops too, the
last visible code may be stale; it is evidence, not a definitive stack trace.
P40 during healthy playback is normal. No support or fix is hardware-confirmed
by compilation or mock tests. The audio RPC/SIF2 driver is unchanged.

Tests on PS2 required:

1. Aladdin S01E01: play from beginning, stop after 1-2 minutes, reopen and resume.
2. Repeat resume at another point; check sound/video sync and Stop/Pause.
3. Shrek (2001): seek forward/back with arrows repeatedly, accepting with X;
   include fast direction changes. Check sound, speed, Stop and Pause.
4. If a failure returns, film the transition and Pxx code. Note whether it is
   resume or seek, approximate time, and whether audio/video both speed up.
5. Keep SMS_SMB_REVIEW_FIX.ELF as rollback. Do not overwrite OPL or SMS settings.

Only player sources/header, tests and this branch's artifact name are changed.
UDPFS, SMB source/blob, codepages, fonts and OPL configuration are not modified.
