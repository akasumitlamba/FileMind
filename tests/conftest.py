import os
# Automated Qt checks do not compete with the user or UI Automation for focus.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
