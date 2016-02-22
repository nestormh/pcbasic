#!/bin/sh
# PC-BASIC install/uninstall script for source distribution

SCRIPT=$0
SPAWNED=$1

DEPS="xdg pygame numpy serial parallel pexpect"
PYTHON="/usr/bin/env python2"

init_package_manager() {
    if [ "$(id -u)" -eq "0" ]; then
        if ( command -v apt-get >/dev/null 2>&1 && command -v apt-mark >/dev/null 2>&1 ); then
            echo "APT package manager found"
            DEB=1
            DEBDEPS="python2.7 python-xdg python-pygame python-numpy python-serial python-parallel python-pexpect xsel"
            MANUAL=$(apt-mark showmanual $DEBDEPS)
        elif ( command -v dnf >/dev/null 2>&1 ); then
            echo "DNF package manager found"
            RPM=1
            # pyparallel is not provided in Fedora repos
            RPMDEPS="python pyxdg pygame numpy pyserial python-pexpect xsel"
            # no dependable way to find manually installed packages
            # (yumdb seems to be broken by dnf)
        fi
    fi
}

install_deps() {
    if [ "$(id -u)" -eq "0" ]; then
        if [ $DEB ]; then
            echo "Installing APT packages $DEBDEPS ..."
            apt-get install $DEBDEPS
        elif [ $RPM ]; then
            echo "Installing RPM packages $RPMDEPS ..."
            dnf install $RPMDEPS
        fi
    fi
}

uninstall_deps() {
    if [ "$(id -u)" -eq "0" ]; then
        if [ $DEB ]; then
            TO_UNINSTALL=$(echo $DEBDEPS $MANUAL | tr ' ' '\n' | sort | uniq -u)
            echo "Uninstalling dependencies ..."
            if [ -n "$TO_UNINSTALL" ]; then
                echo "Marking packages for apt-get autoremove: $TO_UNINSTALL." | tr '\n' ' '
                echo
                apt-mark auto $TO_UNINSTALL
            fi
            if [ -n "$MANUAL" ]; then
                echo "Leaving the previously installed: $MANUAL." | tr '\n' ' '
                echo
            fi
        elif [ $RPM ]; then
            echo "Previously installed dependencies: $RPMDEPS. Please uninstall these packages manually if you no longer need them."
        fi
    fi
}

do_close () {
    if [ "$SPAWNED" = "spawned" ]; then
        echo "Press ENTER to exit."
        read KEY
    fi
    exit 0
}

abort () {
    echo "Installation aborted. No changes were made."
    do_close
}

check_permissions () {
    if [ ! -w $(dirname $INSTALL_DIR) ]; then
        echo
        echo -n "ERROR: You do not have permission to write to "
        dirname $INSTALL_DIR
        abort
    fi
}

check_python () {
    if !( $PYTHON -c 'quit()' 2>/dev/null ); then
        echo
        echo "ERROR: Python 2 not found."
        abort
    fi
}

check_dependencies () {
    DEPS_NOT=""

    echo
    echo "Checking dependencies ... "
    for DEP in $DEPS; do
        echo -n "checking Python module $DEP ... "
        if ( $PYTHON -c "import $DEP" 2>/dev/null ); then
            echo "installed"
        else
            echo "NOT INSTALLED"
            DEPS_NOT="$DEPS_NOT $DEP"
        fi
    done

    if [ -n "$DEPS_NOT" ]; then
        echo
        echo "WARNING: The following Python modules were not found: $DEPS_NOT"
        echo "Please install them separately to ensure all PC-BASIC functionality works correctly."
    fi
}

do_install () {
    cat data/VERSION
    echo "INSTALLATION SCRIPT"
    echo

    #default installation directory
    DEFAULT_DIR="/opt/pcbasic/"
    DESKTOP_DIR="/usr/share/applications"
    ICON_DIR="/usr/share/icons"

    if [ "$(id -u)" != "0" ]; then
        echo -n "NOTE: You are running this script without root privileges, "
        echo "which means you can install PC-BASIC for your user only."
        echo "If you wish to install to a system-wide directory, run this script with root privileges using sudo $0" 1>&2
        echo

        DEFAULT_DIR="$HOME/pcbasic"

        # user's runtime data
        DATA_BASE_DIR=$XDG_DATA_HOME
        if [ -z "$DATA_BASE_DIR" ]; then
            DATA_BASE_DIR="$HOME/.local/share"
        fi
        DATA_DIR="$DATA_BASE_DIR/pcbasic"

        # user's config
        SETTINGS_DIR=$XDG_CONFIG_HOME
        if [ -z "$SETTINGS_DIR" ]; then
            SETTINGS_DIR="$HOME/.config"
        fi
        SETTINGS_DIR="$SETTINGS_DIR/pcbasic"

        DESKTOP_DIR="$DATA_BASE_DIR/applications"
        ICON_DIR="$DATA_BASE_DIR/icons"
    fi

    echo -n "In what directory would you like to install PC-BASIC (default: $DEFAULT_DIR) ? "
    read INSTALL_DIR

    if [ -z "$INSTALL_DIR" ]; then
        INSTALL_DIR="$DEFAULT_DIR"
    fi

    check_permissions
    init_package_manager

    UNINSTALLER="$INSTALL_DIR/uninstall.sh"

    echo
    echo "SUMMARY OF WHAT WILL BE DONE:"
    echo "I will install PC-BASIC to directory $INSTALL_DIR"
    if [ "$(id -u)" = "0" ]; then
        echo "I will create a symbolic link /usr/bin/pcbasic"
        echo "I will create a symbolic link /usr/share/man/man1/pcbasic.1.gz"
    else
        echo "Your user settings will be stored in $SETTINGS_DIR"
        echo "Runtime data will be stored in $DATA_DIR"
    fi

    echo "I will create a desktop menu entry $DESKTOP_DIR/pcbasic.desktop"
    echo "I will create an icon $ICON_DIR/pcbasic.png"
    echo "I will create an uninstall script $UNINSTALLER"

    if [ $DEB ] && [ "$(id -u)" -eq "0" ]; then
        echo "I will install the packages $DEBDEPS"
    fi

    echo
    echo -n "Start installation [y/N] ? "
    read ANSWER

    if [ "$ANSWER" != "y" ] && [ "$ANSWER" != "Y" ]; then
        abort
    fi

    install_deps
    check_python

    echo
    echo "Compiling Python modules ... "

    DIRS="$(find pcbasic/ -type d -print) $(find doc/ -type d -print)"
    FILES="$(find pcbasic/ -type f -print) $(find doc/ -type f -print) $(find .  -maxdepth 1 -type f)"

    # create build environment
    mkdir build
    for dir in $DIRS; do
        if [ "$DIR" != "build" ]; then
            mkdir -p "build/$dir"
        fi
    done

    for file in $FILES; do
        cp "$file" "build/$file"
    done

    # compile sources
    /usr/bin/env python2 -m compileall build/
    # remove source files from build
    rm build/pcbasic/*.py

    cd build/
    # make list of directories and files for uninstall log
    DIRS="$(find pcbasic/ -type d -print) $(find doc/ -type d -print)"
    FILES="$(find pcbasic/ -type f -print) $(find doc/ -type f -print) $(find .  -maxdepth 1 -type f)"
    # invert dirs to delete them recursively
    INVERTED_DIRS=$(echo "$DIRS" | sed '1!G;h;$!d')
    cd ..

    echo
    echo "Copying program files ... "
    mv build/ "$INSTALL_DIR"

    if [ "$(id -u)" = "0" ]; then
        echo "Creating symlinks ... "
        ln -s "$INSTALL_DIR/pcbasic.py" "/usr/bin/pcbasic"
        ln -s "$INSTALL_DIR/doc/pcbasic.1.gz" "/usr/share/man/man1/"
    fi

    echo "Creating menu entry ... "

    DESKTOP_FILE="$DESKTOP_DIR/pcbasic.desktop"
    echo "[Desktop Entry]" > $DESKTOP_FILE
    echo "Name=PC-BASIC" >> $DESKTOP_FILE
    echo "GenericName=GW-BASIC compatible interpreter" >> $DESKTOP_FILE
    echo "Exec=$INSTALL_DIR/pcbasic.py" >> $DESKTOP_FILE
    echo "Terminal=false" >> $DESKTOP_FILE
    echo "Type=Application" >> $DESKTOP_FILE
    echo "Icon=pcbasic" >> $DESKTOP_FILE
    echo "Categories=Development;IDE;" >> $DESKTOP_FILE
    chmod ugo+x $DESKTOP_FILE

    echo "Creating icon ... "
    mkdir -p "$ICON_DIR"
    cp pcbasic.png "$ICON_DIR/pcbasic.png"

    echo "Creating uninstaller ... "
    echo "#!/bin/sh" > $UNINSTALLER
    echo "DESKTOP_DIR=$DESKTOP_DIR" >> $UNINSTALLER
    echo "ICON_DIR=$ICON_DIR" >> $UNINSTALLER
    echo "INSTALL_DIR=$INSTALL_DIR">> $UNINSTALLER
    echo "DEB=$DEB">> $UNINSTALLER
    echo "DEBDEPS='$DEBDEPS'">> $UNINSTALLER
    echo "MANUAL='$MANUAL'">> $UNINSTALLER

    echo "DIRS='$INVERTED_DIRS'" >> $UNINSTALLER
    echo "FILES='$FILES'" >> $UNINSTALLER
    cat $SCRIPT >> $UNINSTALLER
    chmod ugo+x $UNINSTALLER

    check_dependencies

    echo
    echo "INSTALLATION COMPLETED."
    do_close
}

do_uninstall () {
    echo "UNINSTALL PC-BASIC"
    echo

    check_permissions

    echo "SUMMARY OF WHAT WILL BE DONE:"
    echo "I will delete the icon $ICON_DIR/pcbasic.png"
    echo "I will delete the desktop menu entry $DESKTOP_DIR/pcbasic.desktop"
    if [ "$(id -u)" = "0" ]; then
        echo "I will delete the symlink /usr/bin/pcbasic"
        echo "I will delete the symlink /usr/share/man/man1/pcbasic.1.gz"
    fi
    echo "I will delete program files from $INSTALL_DIR"
    echo
    if [ $DEB ] && [ "$(id -u)" -eq "0" ]; then
        echo "I will mark package dependencies for removal"
    fi

    echo -n "Start un-installation [y/N] ?"
    read ANSWER
    if [ "$ANSWER" != "y" ] && [ "$ANSWER" != "Y" ]; then
        abort
    fi
    echo

    echo "Removing icon ... "
    rm "$ICON_DIR/pcbasic.png"

    echo "Removing menu entry ... "
    rm "$DESKTOP_DIR/pcbasic.desktop"

    if [ "$(id -u)" = "0" ]; then
        echo "Removing symlinks ... "
        rm /usr/bin/pcbasic
        rm /usr/share/man/man1/pcbasic.1.gz
    fi

    echo "Removing program files ... "
    for file in $FILES; do
        rm "$INSTALL_DIR/$file"
    done
    for dir in $DIRS; do
        rmdir "$INSTALL_DIR/$dir"
    done
    rm "$INSTALL_DIR/uninstall.sh"
    rmdir "$INSTALL_DIR"

    uninstall_deps

    echo
    echo "UNINSTALL COMPLETED"
}


if [ ! -t 1 ]; then
    if [ "$SPAWNED" = "spawned" ] || [ -z $DISPLAY  ]; then
	    >&2 echo "This script must be run interactively."
        exit 1
    else
	    xterm -e $0 spawned &
	    exit
    fi
fi

if [ $(basename $SCRIPT) = "uninstall.sh" ]; then
    do_uninstall
else
    do_install
fi
