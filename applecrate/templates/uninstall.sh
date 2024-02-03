#!/bin/bash

#Generate application uninstallers for macOS.

#Parameters
DATE=`date +%Y-%m-%d`
TIME=`date +%H:%M:%S`
LOG_PREFIX="[$DATE $TIME]"

#Functions
log_info() {
    echo "${LOG_PREFIX}[INFO]" $1
}

log_warn() {
    echo "${LOG_PREFIX}[WARN]" $1
}

log_error() {
    echo "${LOG_PREFIX}[ERROR]" $1
}

#Check running user
if (( $EUID != 0 )); then
    echo "Please run as root using sudo."
    exit
fi

echo "Welcome to Application Uninstaller"
echo "The following packages will be REMOVED:"
echo "  {{ app }}-{{ version }}"
while true; do
    read -p "Do you wish to continue [Y/n]?" answer
    [[ $answer == "y" || $answer == "Y" || $answer == "" ]] && break
    [[ $answer == "n" || $answer == "N" ]] && exit 0
    echo "Please answer with 'y' or 'n'"
done


#Need to replace these with install preparation script
version={{ version }}
PRODUCT={{ app }}

echo "Application uninstalling process started"

# remove link to shorcut file
# find "/usr/local/bin/" -name "__PRODUCT__-__VERSION__" | xargs rm
# if [ $? -eq 0 ]
# then
#   echo "[1/3] [DONE] Successfully deleted shortcut links"
# else
#   echo "[1/3] [ERROR] Could not delete shortcut links" >&2
# fi

# remove links that were created
{% if link %}
{% for source, target in link %}
echo "Removing link {{ target }}"
[ -e "{{ target }}" ] && rm -rf "{{ target }}"
if [ $? -eq 0 ]
then
    echo "[DONE] Successfully deleted link"
else
    echo "[ERROR] Could not delete link" >&2
fi
{% endfor %}
{% endif %}

{% if install %}
# remove files that were installed
{% for src, target in install %}
echo "Removing {{ target }}"
[ -e "{{ target }}" ] && rm -rf "{{ target }}"
if [ $? -eq 0 ]
then
    echo "[DONE] Successfully deleted application files"
else
    echo "[ERROR] Could not delete application files" >&2
fi
{% endfor %}
{% endif %}

# Remove the application directory
APP_DIR="/Library/Application Support/$PRODUCT/$version"
echo "Removing application support directory: $APP_DIR"
[ -e "$APP_DIR" ] && rm -rf "$APP_DIR"
if [ $? -eq 0 ]
then
    echo "[DONE] Successfully deleted application support directory"
else
    echo "[ERROR] Could not delete application support directory" >&2
fi

#forget from pkgutil
pkgutil --forget "org.$PRODUCT.$version" > /dev/null 2>&1
if [ $? -eq 0 ]
then
    echo "[DONE] Successfully deleted installer receipt"
else
    echo "[ERROR] Could not delete installer receipt" >&2
fi

echo "Application uninstall process finished"
exit 0
