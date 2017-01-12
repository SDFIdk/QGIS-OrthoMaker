# -*- coding: utf-8 -*-
"""
/***************************************************************************
 OrthoMaker
                                 A QGIS plugin
 Pluginn to calculate orthophotos from images and a DEM
                             -------------------
        begin                : 2016-03-15
        copyright            : (C) 2016 by Andrew Flatman / sdfe.dk
        email                : anfla@sdfe.dk
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load OrthoMaker class from file OrthoMaker.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .ortho_maker import OrthoMaker
    return OrthoMaker(iface)
