import ast
from datetime import datetime
from pathlib import Path
from typing import Dict
import unittest
import shutil
import subprocess


class SidebarClockTests(unittest.TestCase):
    def parts(self, hour, minute):
        source = (Path(__file__).parents[1] / "streamlit_app" / "app.py").read_text(encoding="utf-8")
        function = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == "clock_parts")
        scope = {"Dict": Dict, "_user_now": lambda: datetime(2026, 10, 4, hour, minute)}
        exec(compile(ast.Module(body=[function], type_ignores=[]), "clock_parts", "exec"), scope)
        return scope["clock_parts"]()

    def test_hands_match_display_and_hour_progress(self):
        for hour, minute, hour_angle, minute_angle in [
            (0, 0, 0, 0), (12, 0, 0, 0), (3, 30, 105, 180),
            (9, 45, 292.5, 270), (23, 59, 359.5, 354),
        ]:
            with self.subTest(hour=hour, minute=minute):
                result = self.parts(hour, minute)
                self.assertEqual(float(result["hour_angle"]), hour_angle)
                self.assertEqual(float(result["minute_angle"]), minute_angle)
                self.assertEqual(result["time"], f"{hour % 12 or 12}:{minute:02d}")

    def test_browser_ticks_rollover_and_cleanup_without_python_events(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is needed for the browser clock regression test")
        source = (Path(__file__).parents[1] / "streamlit_app" / "sidebar_clock.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        js = next(ast.literal_eval(n.value) for n in tree.body
                  if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "CLOCK_JS" for t in n.targets))
        self.assertNotIn("setStateValue", js)
        self.assertNotIn("setTriggerValue", js)
        harness = r"""
const assert = require('node:assert/strict');
const NativeDate = Date;
let current = new NativeDate(2026, 9, 4, 23, 59, 59);
global.Date = class extends NativeDate { constructor(...args) { super(...(args.length ? args : [current.getTime()])); } };
const fields = Object.fromEntries(['.clock_time','.clock_ampm','.clock_day','.clock_date'].map(k=>[k,{textContent:''}]));
const hands = [0,1].map(()=>({setAttribute(k,v){ this[k]=v; }}));
const root = {querySelector:s=>fields[s], querySelectorAll:()=>hands};
let tick, visible, cleared = false, removed = false;
global.window = {setInterval(fn,ms){assert.equal(ms,1000);tick=fn;return 7;},clearInterval(id){assert.equal(id,7);cleared=true;}};
global.document = {hidden:false,addEventListener(name,fn){visible=fn;},removeEventListener(name,fn){assert.equal(fn,visible);removed=true;}};
const cleanup = render({parentElement:{querySelector:()=>root},data:{html:''}});
assert.equal(fields['.clock_time'].textContent,'11:59');
assert.equal(fields['.clock_ampm'].textContent,'PM');
assert.equal(hands[1].transform,'rotate(359.9 16 16)');
current = new NativeDate(2026,9,5,0,0,0); tick();
assert.equal(fields['.clock_time'].textContent,'12:00');
assert.equal(fields['.clock_ampm'].textContent,'AM');
assert.equal(fields['.clock_date'].textContent,'Oct 5, 2026');
assert.equal(hands[0].transform,'rotate(0 16 16)');
current = new NativeDate(2026,9,5,3,30,30); visible();
assert.equal(hands[0].transform,'rotate(105.25 16 16)');
assert.equal(hands[1].transform,'rotate(183 16 16)');
cleanup(); assert.ok(cleared && removed);
"""
        code = "const render = " + js.replace("export default", "", 1) + ";\n" + harness
        result = subprocess.run([node, "-"], input=code, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
