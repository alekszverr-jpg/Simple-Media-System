"""Compile the actual restart helper against a stateful mock demuxer.

This checks CPU-side restart ordering, not PS2 DMA, scheduling or playback.
"""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parent.parent
source = (root / 'src/SMS_PlayerControl.c').read_text()
start = source.index('static int _restart_after_preview (')
end = source.index('\nstatic int PlayerControl_Scroll (', start)
helper = source[start:end]
harness = r'''
#include <stdint.h>
#include <assert.h>
#include <stdio.h>
typedef struct FileContext {
 unsigned m_CurPos, m_StreamSize;
 int (*Stream)(struct FileContext*, unsigned, unsigned);
} FileContext;
typedef struct SMS_Container {
 FileContext *m_pFileCtx;
 int (*Seek)(struct SMS_Container*, int, int, int64_t);
} SMS_Container;
static struct { int m_VideoIdx; } s_Player = { 2 };
static int phase, fail_seek, fail_stream, counters, expected_dir;
static int64_t expected_pos;
static int stream(FileContext *f, unsigned pos, unsigned blocks) {
 if (!blocks) { assert(phase == 0); assert(pos == f->m_CurPos); phase = 1; return 0; }
 assert(phase == 2); assert(pos == 1000); assert(counters == expected_pos);
 assert(blocks == 384); phase = 3; return fail_stream ? -1 : 2048;
}
static int seek(SMS_Container *c, int idx, int dir, int64_t pos) {
 assert(phase == 1); assert(idx == 2); assert(dir == expected_dir);
 assert(pos == expected_pos); phase = 2;
 if(fail_seek) return 0;
 counters = (int)pos; c->m_pFileCtx->m_CurPos = 1000; return 1;
}
'''
harness += helper
harness += r'''
int main(void) {
 FileContext f = { 9000, 384, stream };
 SMS_Container c = { &f, seek };
 unsigned checks = 0;
 for (int dir = -1; dir <= 1; dir += 2)
  for (int n = 0; n < 1000; ++n)
   for(int failure = 0; failure < 3; ++failure) {
    phase = 0; counters = 9999; f.m_CurPos = 9000;
    expected_dir = dir; expected_pos = n;
    fail_seek = failure == 1; fail_stream = failure == 2;
    assert(_restart_after_preview(&c, dir, n) == (failure == 0));
    assert(phase == (fail_seek ? 2 : 3)); ++checks;
   }
 printf("PASS: %u player restart cases (including failed seek/refill)\n", checks);
}
'''
with tempfile.TemporaryDirectory() as temp:
    c = Path(temp) / 'seek.c'
    exe = Path(temp) / 'seek'
    c.write_text(harness)
    subprocess.run([os.environ.get('CC', 'cc'), '-std=c99', '-Wall', '-Wextra',
                    '-Werror', '-fsanitize=address,undefined',
                    '-fno-sanitize-recover=all', str(c), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)

player = (root / 'src/SMS_Player.c').read_text()
assert 'lResumeTime >= 0 && s_Player.m_VideoTime > 0' in player
assert player.index('PlayerControl_Init ();') < player.index('PlayerControl_Resume ( lResumeTime )')
assert 'PlayerControl_Scroll ( -1, aTime )' in source
print('PASS: resume is deferred until initial video frames, uses common seek path')
