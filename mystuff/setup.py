from setuptools import setup

setup(
    name="Panda-chan and the Endless Horde",
    options={
        "build_apps": {
            "include_patterns": [
                "**/*.png",
                "**/*.ogg",
                "**/*.txt",
                "**/*.egg",
                "fonts/*"
            ],
            "gui_apps": {
                "Panda-chan and the Endless Horde": "Game.py"
            },
            "plugins": [
                "pandagl",
                "p3openal_audio"
            ],
            "platforms": [],
            "log_filename": "$USER_APPDATA/PandaChanAndHorde/output.log",
            "log_append": False
        }
    }
)
