# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from labman.db.testing import LabmanTestCase
from labman.db.equipment import EquipmentType, Equipment


class TestEquipmentType(LabmanTestCase):
    # The description property is indirectly tested during the create test
    def test_create(self):
        obs = EquipmentType.create('Robot')
        self.assertEqual(obs.description, 'Robot')


class TestEquipment(LabmanTestCase):
    def test_create(self):
        et = EquipmentType.create('Robot')
        obs = Equipment.create('MIKA', et, notes='Lazy on fridays')
        self.assertEqual(obs.external_id, 'MIKA')
        self.assertEqual(obs.equipment_type, et)
        self.assertEqual(obs.notes, 'Lazy on fridays')

        obs = Equipment.create('AKIM', et)
        self.assertEqual(obs.external_id, 'AKIM')
        self.assertEqual(obs.equipment_type, et)
        self.assertIsNone(obs.notes)

    def test_notes_setter(self):
        et = EquipmentType.create('Sequencer')
        obs = Equipment.create('CHARLES', et)
        self.assertIsNone(obs.notes)
        obs.notes = 'Needs maintenance'
        self.assertEqual(obs.notes, 'Needs maintenance')
        obs.notes = None
        self.assertIsNone(obs.notes)


if __name__ == '__main__':
    main()
