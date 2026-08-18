FROM kicad/kicad:10.0.4

# InteractiveHtmlBom (github.com/openscopeproject/InteractiveHtmlBom)
# imports pcbnew directly, so it has to run inside a KiCad install, not a
# plain Python image -- see README.md for how this was figured out.
USER root
RUN apt-get update && apt-get install -y --no-install-recommends python3-pip \
    && rm -rf /var/lib/apt/lists/*

# --no-deps: the PyPI package declares wxPython as a hard dependency, but
# wx is only needed for the GUI config dialog (--show-dialog) and the
# live "Generate Interactive HTML BOM" button inside Pcbnew's own UI --
# neither of which this Dockerfile's CLI-only usage touches. Building
# wxPython from source (no prebuilt wheel for this base image) is slow
# and unnecessary; skip it.
RUN pip install --no-deps --break-system-packages InteractiveHtmlBom

# The upstream image's non-root "kicad" user already matches a typical
# host uid (1000), so output files land owned by the host user.
USER kicad

# Both of these matter -- see README.md "Why two environment variables":
#   CLI_MODE      skips registering this as a live Pcbnew GUI plugin
#                 (which asserts without a running KiCad app instance)
#   NO_DISPLAY    tells the CLI entry point not to require wx at all
#                 (otherwise it exits with "wxpython is required...")
ENV INTERACTIVE_HTML_BOM_CLI_MODE=1
ENV INTERACTIVE_HTML_BOM_NO_DISPLAY=1

ENTRYPOINT ["python3", "-m", "InteractiveHtmlBom.generate_interactive_bom", "--no-browser"]
