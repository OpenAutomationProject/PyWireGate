#!/usr/bin/env python
# -*- coding: utf-8 -*-
## -----------------------------------------------------
## CodeClass.py
## -----------------------------------------------------
## Copyright (c) 2011, Christian Mayer, All rights reserved.
##
## This program is free software; you can redistribute it and/or modify it under the terms
## of the GNU General Public License as published by the Free Software Foundation; either
## version 3 of the License, or (at your option) any later version.
##
## This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
## without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
## See the GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License along with this program;
## if not, see <http://www.gnu.de/documents/gpl-3.0.de.html>.

class CodeClass:
  """The object that contains the code to run from the task manager and the
  definied entry points for that"""
  def getParameter( self, parameter ):
    return getattr( self, parameter )
    
  def setParameter( self, parameter, value ):
    setattr( self, parameter, value )