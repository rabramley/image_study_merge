import time
from flask import render_template, request, redirect, url_for
from image_study_merge.model import DataDictionary, StudyData, StudyDataColumn
from lbrc_flask.forms import SearchForm, FlashingForm
from lbrc_flask.database import db
from itertools import groupby
from functools import lru_cache
from wtforms import StringField, FormField, FieldList, Form, HiddenField, IntegerField
from wtforms_components import SelectField
from .. import blueprint


@lru_cache
def _data_dictionary_choices(time_to_live):
    data_dictionary = []

    for k, g in groupby(DataDictionary.query.all(), lambda dd: dd.group_name):
        data_dictionary.append((
            k,
            [(dd.field_name, dd.field_label ) for dd in g]
        ))

    return [('', '[No Mapping]')] + data_dictionary


def data_dictionary_choices():
    return _data_dictionary_choices(time_to_live=round(time.time() / 60))


class MappingForm(Form):
    id = HiddenField('Id')
    column_number = IntegerField('Column Number')
    name = StringField('Source', render_kw={'readonly': True})
    mapping = SelectField(
        'Destination',
        choices=data_dictionary_choices,
        default='',
        validate_choice=False,
    )


class MappingsForm(FlashingForm):
    fields = FieldList(FormField(MappingForm))


@blueprint.route("/column_mapping/<int:id>", methods=['GET', 'POST'])
def column_mapping(id):
    study_data = StudyData.query.get_or_404(id)

    search_form = SearchForm(formdata=request.args)

    q = StudyDataColumn.query.filter(StudyDataColumn.study_data_id == id)

    if search_form.search.data:
        q = q.filter(StudyDataColumn.name.like(f'%{search_form.search.data}%'))

    mapping_form = MappingsForm(data={
        'fields': q.all(),
    })

    return render_template(
        "ui/column_mapping/index.html",
        study_data=study_data,
        search_form=search_form,
        mapping_form=mapping_form,
    )


@blueprint.route("/column_mapping/<int:id>/save", methods=['POST'])
def column_mapping_save(id):
    study_data = StudyData.query.get_or_404(id)

    columns = {str(c.id): c for c in study_data.columns}

    form = MappingsForm()

    if form.validate_on_submit():
        for field in form.fields:
            columns[field.data['id']].mapping = field.data['mapping']

    db.session.add_all(columns.values())
    db.session.commit()

    return redirect(url_for('ui.column_mapping', id=id))