import React from 'react';
import { 
    List, 
    Datagrid, 
    TextField, 
    Edit, 
    Create, 
    SimpleForm, 
    TextInput 
} from 'react-admin';

/**
 * Affiche la liste des catégories.
 */
export const CategoryList = () => (
    <List>
        <Datagrid rowClick="edit">
            <TextField source="id" />
            <TextField source="name" label="Nom" />
            <TextField source="description" label="Description" />
            {/* TODO: Afficher la catégorie parente si nécessaire (ReferenceField) */}
            {/* <ReferenceField source="parent_category_id" reference="categories">
                <TextField source="name" label="Catégorie Parente" />
            </ReferenceField> */}
        </Datagrid>
    </List>
);

/**
 * Formulaire d'édition pour une catégorie.
 */
export const CategoryEdit = () => (
    <Edit mutationMode="pessimistic">
        <SimpleForm>
            <TextInput source="id" disabled />
            <TextInput source="name" label="Nom" required fullWidth />
            <TextInput source="description" label="Description" multiline fullWidth />
            {/* TODO: Sélection de la catégorie parente (ReferenceInput) */}
            {/* <ReferenceInput source="parent_category_id" reference="categories">
                <SelectInput optionText="name" label="Catégorie Parente" fullWidth allowEmpty />
            </ReferenceInput> */}
        </SimpleForm>
    </Edit>
);

/**
 * Formulaire de création pour une catégorie.
 */
export const CategoryCreate = () => (
    <Create redirect="list">
        <SimpleForm>
            <TextInput source="name" label="Nom" required fullWidth />
            <TextInput source="description" label="Description" multiline fullWidth />
             {/* TODO: Sélection de la catégorie parente (ReferenceInput) */}
            {/* <ReferenceInput source="parent_category_id" reference="categories">
                <SelectInput optionText="name" label="Catégorie Parente" fullWidth allowEmpty />
            </ReferenceInput> */}
        </SimpleForm>
    </Create>
); 