# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated, HTTPError

from labman.gui.handlers.base import BaseHandler


class PlateHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_id = int(self.get_argument('plate_id'))

        # Check if the plate exists
        # TODO: change for an actual check
        if plate_id != 1:
            raise HTTPError(404, "Plate %s does not exist" % plate_id)

        # TODO: get this info from the DB
        plate_name = "AG110"

        self.render("plate.html", plate_id=plate_id, plate_name=plate_name)


class PlateLayoutHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_id = int(self.get_argument('plate_id'))

        # Check if the plate exists
        # TODO: change for an actual check
        if plate_id != 1:
            raise HTTPError(404, "Plate %s does not exist" % plate_id)

        # TODO: get this info from the DB
        result = {'rows': 8,
                  'cols': 12,
                  'editable': True}

        self.write(result)
        self.finish()
