Mexican Payroll
===============

Added attributes required to generate the Mexican Payroll CFDI, and
allow send to stamp the documents with SAT.

Generated documents for version 1.3, based on SAT document:
https://goo.gl/L4KFZu

Added button to confirm and sign all the payslips from a payslips batch.
This button allows to confirm or retry (in case of fail) the signing process.

Fields added to get all attributes to Complement:

In payroll are added the next fields:

.. image:: l10n_mx_edi_payslip/static/src/img/payroll_cfdi.png

- PAC status: This field get the CFDI status, and have the button "Retry"
  to be used when the CFDI could not be stamped.
- SAT status: This field save the CFDI status in SAT system, could be
  calculated with the button "Retry" when the SAT status change.

The Complement have 6 nodes to be added when is generated

.. image:: l10n_mx_edi_payslip/static/src/img/payroll_nodes.png

**Emisor**

  This attribute come from company that generate the documents

  To get the attributes was added the next fields on company model:

  - Employer Registration
  - CURP (To Natutal Person)
  - Source Resource (When apply the attribute OrigenRecurso)

**Receptor**

  This attribute come from employee information

  To get node attributes are used:

  From employee:

  - CURP
  - NSS
  - Syndicated
  - Category in yellow
  - Fiscal Regime
  - Department
  - Job Title
  - Risk Rank: Could be empty if is set the employer registration,
    and the value comes from it.
  - Bank Account Number
  - Working Address
  - Employer Registration: If the company has multiple employer
    registrations, could be defined this value for each employee.

  From contract

  - Scheduled Pay
  - Wage
  - Integrated Salary

**Percepciones**

  This attribute come from payslip inputs and are divided in two groups
  (taxed and exempt), and each have a category to indicate each one.

  To define one perception taxed in payslip inputs the code must be
  pg_codeNumber defined by the SAT.

  To define one perception exempt in payslip inputs the code must be
  pe_codeNumber defined by the SAT.

  - To perceptions with code 002 - "Horas extra", is added the field
    "Extra Hours" on payslip, where must be added all records that will
    be added in the node "HorasExtra" to that perception.

    .. image:: l10n_mx_edi_payslip/static/src/img/extra_hours.png
       :width: 700pt

  - To perceptions with code 045 - "Ingresos en acciones o titulos valor
    que representan bienes" is need add the node "AccionesOTitulos" in the
    perception, to this was added new field in notebook "TECHNICAL CFDI
    INFORMATION", where could be assined the amounts to taxed or exempt.
    In this must be assigned the category that indicate if is perception
    taxed or excempt.

    .. image:: l10n_mx_edi_payslip/static/src/img/action_titles.png
       :width: 400pt

  - If the payroll have perceptions with code 022, 023 or 025, the node
    "SeparacionIndemnizacion" must be added in the CFDI, to assign the data
    to this node, is added the field "Retirement / Indemnity" where must
    be added a record with node type = "SeparacionIndemnizacion", and
    this have the fields required to each attribute to this node.

    .. image:: l10n_mx_edi_payslip/static/src/img/separacion_indemnizacion.png
       :width: 700pt

  - If the payroll have perceptions with code 039 or 044, the node
    "JubilacionPensionRetiro" must be added in the CFDI, to assign the data
    to this node, is added the field "Retirement / Indemnity" where must
    be added a record with node type = "JubilacionPensionRetiro", and
    this have the fields required to each attribute to this node.
    If perception is to "Jubilaciones, pensiones o haberes de retiro",
    the value in amount total is used to node "TotalUnaExhibicion", or, if
    is "Jubilaciones, pensiones o haberes de retiro en parcialidades", the
    value in amount total is used to node "TotalParcialidad".
    When perception code is 039, the value in Amount daily must be 0.0.

    .. image:: l10n_mx_edi_payslip/static/src/img/jubilacion_pension_retiro.png
       :width: 700pt

**Deducciones**

  This attribute come from payslip inputs

  The deductions have the category "Deduction" to be identified, and to
  indicate that a line in payslip inputs must be have the code d_codeNumber
  defined by the SAT.

**OtrosPagos**

  This attribute come from payslip inputs

  The other payments have the category "Other Payments" to be
  identified, and to indicate that a line in payslip inputs must be
  have the code op_codeNumber defined by the SAT.

  - To other payments with code 002 - "Subsidio para el empleo", is added
    the field "Subsidy Caused" in notebook "TECHNICAL CFDI INFORMATION",
    where must be added the value that will be added in the node
    "SubsidioAlEmpleo" to that payment.

    .. image:: l10n_mx_edi_payslip/static/src/img/subsidio_empleo.png
       :width: 400pt

  - To ather payments with code 004 - "Aplicación de saldo a favor por
    compensación anual", are added the fields "Balance in Favor", "Year"
    and "Remaining" in notebook "TECHNICAL CFDI INFORMATION", where must
    be assigned the attributes to will be added in the node
    "CompensacionSaldosAFavor" to that payment.

    .. image:: l10n_mx_edi_payslip/static/src/img/balances_in_favor.png
       :width: 400pt

**Incapacidades**

  This attribute come from payslip inabilities

  When is added an deduction with code 006 "Descuento por incapacidad"
  must be added in the payslip the records that will be added in
  this node. Else, not must be added any record in the payslip
  inabilities.

Extra Features
--------------

**Make the Perception/Deduction dynamic**

  The attribute ``Concepto`` on ``Perceptions`` and ``Deductions`` is open, and could
  be used the name assigned by the SAT, for example ``Comisiones`` or the value that the company
  prefers, for example ``Comisión por ventas en el mes``, in that case must be marked the option
  ``Dynamic Concepts`` on the company settings for payroll, and will to take the name assigned
  on the payroll inputs.

**Send payslips PDF and CFDI to your employees**

  A new ``Enviar por correo electrónico`` button was added, this button will allow to
  send a the payslips PDF and CFDI to the employees easily.

  .. image:: l10n_mx_edi_payslip/static/src/img/send_email.png
      :width: 400pt

  - Set the employee personal email in the contact related to the employee.

    .. image:: l10n_mx_edi_payslip/static/src/img/employee_private_email.png
       :width: 400pt

    .. image:: l10n_mx_edi_payslip/static/src/img/partner_private_email.png
       :width: 400pt

  - If the private email is not set, the emails used will be the work email.

    .. image:: l10n_mx_edi_payslip/static/src/img/work_email.png
       :width: 400pt


Configuration
=============

To configure this module, you need to install the Attendances Module in order to use the following salary rules:

  - Séptimo dia
  - Prima dominical.
  - Días de Descanso Trabajados

- This rules will not work, without attendances module.
- Usually Attendances Module is used with a time clock, however, it is not necessary to use one to use this rules, you can register the attendances manually using any valid way.
- It is possible to select one o more payslips on the list view and download the PDF and the XML in a single zip file. In order to do that, please install the module l10n_mx_edi_uuid_zip and go to the server action Download Payslip UUID XML and Create Contextual Action.


Credits
=======

**Contributors**

* Nhomar Hernández <nhomar@vauxoo.com> (Planner/Auditor)
* Luis Torres <luis_t@vauxoo.com> (Developer)

Maintainer
==========

.. image:: https://s3.amazonaws.com/s3.vauxoo.com/description_logo.png
   :alt: Vauxoo
