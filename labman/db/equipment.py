# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from labman.db.sql_connection import TRN
from labman.db.base import LabmanObject


class EquipmentType(LabmanObject):
    """Equipment type object

    Attributes
    ----------
    description

    Methods
    -------
    create

    See Also
    --------
    labman.db.base.LabmanObject
    """
    _table = 'qiita.equipment_type'
    _id_column = 'equipment_type_id'

    @classmethod
    def create(cls, description):
        """Creates a new equipment type in the system

        Parameters
        ----------
        description : str
            Short description of the Equipment Type

        Returns
        -------
        labman.db.equipment.EquipmentType
            The newly created equipment type
        """
        with TRN:
            sql = """INSERT INTO qiita.equipment_type (description)
                     VALUES (%s)
                     RETURNING equipment_type_id"""
            TRN.add(sql, [description])
            return cls(TRN.execute_fetchlast())

    @property
    def description(self):
        """The description of the equipment type"""
        return self._get_attr('description')


class Equipment(LabmanObject):
    """Equipment object

    Attributes
    ----------
    external_id
    equipment_type
    notes

    Methods
    -------
    create
    """
    _table = 'qiita.equipment'
    _id_column = 'equipment_id'

    @classmethod
    def create(cls, external_id, equipment_type, notes=None):
        """Creates a new equipment entry in the system

        Parameters
        ----------
        external_id : str
            Equipment's external identifier
        equipment_type : labman.db.equipment.EquipmentType
            The equipment's type
        notes : str, optional
            Notes for the equipment

        Returns
        -------
        labman.db.equipment.Equipment
            The newly created equipment
        """
        with TRN:
            sql = """INSERT INTO qiita.equipment
                        (external_id, equipment_type_id, notes)
                     VALUES (%s, %s, %s)
                     RETURNING equipment_id"""
            TRN.add(sql, [external_id, equipment_type.id, notes])
            return cls(TRN.execute_fetchlast())

    @property
    def external_id(self):
        "The equipment's external identifier"
        return self._get_attr('external_id')

    @property
    def equipment_type(self):
        "The equipment's type"
        return EquipmentType(self._get_attr('equipment_type_id'))

    @property
    def notes(self):
        "The equipment's notes"
        return self._get_attr('notes')

    @notes.setter
    def notes(self, value):
        "Set the new value for the notes attribute"
        self._set_attr('notes', value)
