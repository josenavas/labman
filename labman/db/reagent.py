# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from labman.db.sql_connection import TRN
from labman.db.base import LabmanObject


class ReagentType(LabmanObject):
    """Reagent type object

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
    _table = 'qiita.reagent_type'
    _id_column = 'reagent_type_id'

    @classmethod
    def create(cls, description):
        """Creates a new reagent type in the system

        Parameters
        ----------
        description : str
            Short description of the Reagent Type

        Returns
        -------
        labman.db.reagent.ReagentType
            The newly created reagent type
        """
        with TRN:
            sql = """INSERT INTO qiita.reagent_type (description)
                     VALUES (%s)
                     RETURNING reagent_type_id"""
            TRN.add(sql, [description])
            return cls(TRN.execute_fetchlast())

    @property
    def description(self):
        """The description of the reagent type"""
        return self._get_attr('description')


class Reagent(LabmanObject):
    """Reagent object

    Attributes
    ----------
    external_lot_id
    reagent_type
    notes

    Methods
    -------
    create
    """
    _table = 'qiita.reagent'
    _id_column = 'reagent_id'

    @classmethod
    def create(cls, external_lot_id, reagent_type, notes=None):
        """Creates a new reagent entry in the system

        Parameters
        ----------
        external_lot_id : str
            Reagent's external identifier
        reagent_type : labman.db.reagent.ReagentType
            The reagent's type
        notes : str, optional
            Notes for the reagent

        Returns
        -------
        labman.db.reagent.Reagent
            The newly created reagent
        """
        with TRN:
            sql = """INSERT INTO qiita.reagent
                        (external_lot_id, reagent_type_id, notes)
                     VALUES (%s, %s, %s)
                     RETURNING reagent_id"""
            TRN.add(sql, [external_lot_id, reagent_type.id, notes])
            return cls(TRN.execute_fetchlast())

    @property
    def external_lot_id(self):
        "The reagent's external identifier"
        return self._get_attr('external_lot_id')

    @property
    def reagent_type(self):
        "The reagent's type"
        return ReagentType(self._get_attr('reagent_type_id'))

    @property
    def notes(self):
        "The reagent's notes"
        return self._get_attr('notes')

    @notes.setter
    def notes(self, value):
        "Set the new valule for the notes attribute"
        self._set_attr('notes', value)
