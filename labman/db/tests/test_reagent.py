# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from labman.db.testing import LabmanTestCase
from labman.db.reagent import ReagentType, Reagent


class TestReagentType(LabmanTestCase):
    # The description property is indirectly tested during the create test
    def test_create(self):
        obs = ReagentType.create('Extraction Kit')
        self.assertEqual(obs.description, 'Extraction Kit')


class TestReagent(LabmanTestCase):
    def test_create(self):
        rt = ReagentType.create('Extraction Kit')
        obs = Reagent.create('LOT1234', rt, notes='Contaminated')
        self.assertEqual(obs.external_lot_id, 'LOT1234')
        self.assertEqual(obs.reagent_type, rt)
        self.assertEqual(obs.notes, 'Contaminated')

        obs = Reagent.create('LOT4321', rt)
        self.assertEqual(obs.external_lot_id, 'LOT4321')
        self.assertEqual(obs.reagent_type, rt)
        self.assertIsNone(obs.notes)

    def test_notes_setter(self):
        rt = ReagentType.create('Master Mix')
        obs = Reagent.create('L12', rt)
        self.assertIsNone(obs.notes)
        obs.notes = 'Contaminated'
        self.assertEqual(obs.notes, 'Contaminated')
        obs.notes = None
        self.assertIsNone(obs.notes)


if __name__ == '__main__':
    main()
