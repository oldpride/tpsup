#!/usr/bin/perl

# https://stackoverflow.com/questions/69559859/perl-eval-scope/

use File::Basename;
use lib dirname (__FILE__);
use test_eval_scope;

test_eval_scope::f1();
