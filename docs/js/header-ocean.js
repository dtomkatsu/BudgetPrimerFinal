/*
 * header-ocean.js — a subtle animated WebGL ocean behind the masthead.
 *
 * A living version of the three-swell wordmark: a few soft sea-foam swell
 * lines drift across the lower band of the header, pooling just above the
 * white "shore" curve. Decorative only (aria-hidden), and deliberately cheap.
 *
 * Why raw WebGL and not three.js: this is ~3 KB and pulls in no dependency —
 * three.js would add ~150 KB gzipped for what one fragment shader does here.
 *
 * Performance guarantees (matters because the tracker is embedded in iframes
 * on other sites, where a runaway GPU loop would drain the host page):
 *   • prefers-reduced-motion  → never starts; the static gradient + SVG swell
 *     remain the experience.
 *   • no WebGL / shader error / context loss → silently removes the canvas and
 *     falls back to the existing static header.
 *   • pauses the rAF loop when the header scrolls off-screen (IntersectionObserver)
 *     and when the tab is hidden (visibilitychange).
 *   • caps devicePixelRatio at 1.5 so it never renders more pixels than it must.
 */
(function () {
    'use strict';

    function init() {
        const header = document.querySelector('.app-header');
        if (!header) return;
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

        const canvas = document.createElement('canvas');
        canvas.className = 'app-header-ocean';
        canvas.setAttribute('aria-hidden', 'true');
        header.insertBefore(canvas, header.firstChild);

        const gl = canvas.getContext('webgl', { alpha: true, antialias: true,
            premultipliedAlpha: false, depth: false, powerPreference: 'low-power' })
            || canvas.getContext('experimental-webgl');
        if (!gl) { canvas.remove(); return; }

        const VERT = `
            attribute vec2 a_pos;
            void main() { gl_Position = vec4(a_pos, 0.0, 1.0); }`;

        // Three drifting swell lines (echoing the 3-swell wordmark), soft
        // sea-foam white, alpha pooling toward the bottom of the band.
        const FRAG = `
            precision mediump float;
            uniform vec2 u_resolution;
            uniform float u_time;
            void main() {
                vec2 uv = gl_FragCoord.xy / u_resolution;
                float t = u_time;
                float acc = 0.0;
                for (int i = 0; i < 3; i++) {
                    float fi = float(i);
                    float base = 0.16 + fi * 0.14;
                    float disp =
                        0.022 * sin(uv.x * (7.0 + fi * 3.0) + t * (0.5 + fi * 0.25) + fi * 1.7)
                      + 0.014 * sin(uv.x * (15.0 - fi * 2.0) - t * (0.7 + fi * 0.2));
                    float d = abs(uv.y - (base + disp));
                    acc += smoothstep(0.045, 0.0, d) * (0.18 + fi * 0.10);
                }
                float fade = smoothstep(0.92, 0.04, uv.y);   // pool near the shore
                vec3 foam = vec3(0.88, 0.96, 0.94);
                float alpha = clamp(acc, 0.0, 1.0) * fade * 0.8;
                gl_FragColor = vec4(foam, alpha);
            }`;

        function compile(type, src) {
            const s = gl.createShader(type);
            gl.shaderSource(s, src);
            gl.compileShader(s);
            if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) { gl.deleteShader(s); return null; }
            return s;
        }
        const vs = compile(gl.VERTEX_SHADER, VERT);
        const fs = compile(gl.FRAGMENT_SHADER, FRAG);
        if (!vs || !fs) { canvas.remove(); return; }
        const prog = gl.createProgram();
        gl.attachShader(prog, vs); gl.attachShader(prog, fs); gl.linkProgram(prog);
        if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) { canvas.remove(); return; }

        gl.useProgram(prog);
        const buf = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, buf);
        gl.bufferData(gl.ARRAY_BUFFER,
            new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
        const aPos = gl.getAttribLocation(prog, 'a_pos');
        gl.enableVertexAttribArray(aPos);
        gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);
        const uTime = gl.getUniformLocation(prog, 'u_time');
        const uRes = gl.getUniformLocation(prog, 'u_resolution');
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
        gl.clearColor(0, 0, 0, 0);

        function resize() {
            const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
            const w = Math.max(1, Math.round(header.clientWidth * dpr));
            const h = Math.max(1, Math.round(header.clientHeight * dpr));
            if (canvas.width !== w || canvas.height !== h) {
                canvas.width = w; canvas.height = h;
                gl.viewport(0, 0, w, h);
            }
        }
        resize();
        if (typeof ResizeObserver !== 'undefined') {
            new ResizeObserver(resize).observe(header);
        } else {
            window.addEventListener('resize', resize);
        }

        let rafId = 0;
        let onScreen = true;
        const t0 = performance.now();
        function frame() {
            rafId = 0;
            if (!onScreen || document.hidden) return;        // paused → stop the loop
            gl.uniform1f(uTime, (performance.now() - t0) / 1000);
            gl.uniform2f(uRes, canvas.width, canvas.height);
            gl.clear(gl.COLOR_BUFFER_BIT);
            gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
            rafId = requestAnimationFrame(frame);
        }
        function play() { if (!rafId && onScreen && !document.hidden) rafId = requestAnimationFrame(frame); }
        function stop() { if (rafId) { cancelAnimationFrame(rafId); rafId = 0; } }

        // Pause when the header is scrolled out of view (cheap when embedded).
        if (typeof IntersectionObserver !== 'undefined') {
            new IntersectionObserver((entries) => {
                onScreen = entries[0].isIntersecting;
                onScreen ? play() : stop();
            }, { threshold: 0 }).observe(header);
        }
        document.addEventListener('visibilitychange', () => document.hidden ? stop() : play());

        // Lost GPU context → drop to the static fallback for good.
        canvas.addEventListener('webglcontextlost', (e) => { e.preventDefault(); stop(); canvas.remove(); });

        play();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
