#!/bin/bash
rm dqlogger_t wxtlogger_t
gcc dqlogger/dqlogger.c -o dqlogger_t -lm
gcc wxtlogger/wxtlogger.c -o wxtlogger_t -lm
