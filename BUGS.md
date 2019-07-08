# Bugs
This document lists known bugs.
They are sorted by their (security) impact.

Please keep in mind that BL4P is experimental and unfinished software.
There are probably lots of bugs that do exist even if they are not listed here.
The main purpose of this list is to act as a reminder for developers on what
has to be fixed.

## Sub-optimal trading

### All orders are immediately active
This is not necessarily desired behavior: it might be preferred to first
execute the most preferred orders, before activating less preferred orders.


