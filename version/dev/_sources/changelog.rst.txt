.. _ref_release_notes:

Release notes
#############

This document contains the release notes for the project.

.. vale off

.. towncrier release notes start

`0.1.1 <https://github.com/ansys/pyresultexplorer/releases/tag/v0.1.1>`_ - September 02, 2026
=============================================================================================

.. tab-set::


  .. tab-item:: Added

    .. list-table::
        :header-rows: 0
        :widths: auto

        * - Ci: adding release environment
          - `#158 <https://github.com/ansys/pyresultexplorer/pull/158>`_


  .. tab-item:: Fixed

    .. list-table::
        :header-rows: 0
        :widths: auto

        * - Fix: pdf build process needs path adaptation
          - `#159 <https://github.com/ansys/pyresultexplorer/pull/159>`_


  .. tab-item:: Documentation

    .. list-table::
        :header-rows: 0
        :widths: auto

        * - Bump the sphinx-dependencies group with 2 updates
          - `#155 <https://github.com/ansys/pyresultexplorer/pull/155>`_

        * - Chore: update CHANGELOG for v0.1.0
          - `#157 <https://github.com/ansys/pyresultexplorer/pull/157>`_


  .. tab-item:: Dependencies

    .. list-table::
        :header-rows: 0
        :widths: auto

        * - Bump pytest-rerunfailures from 16.4 to 16.6 in the pytest-dependencies group
          - `#154 <https://github.com/ansys/pyresultexplorer/pull/154>`_


  .. tab-item:: Maintenance

    .. list-table::
        :header-rows: 0
        :widths: auto

        * - Bump the actions-deps group with 2 updates
          - `#156 <https://github.com/ansys/pyresultexplorer/pull/156>`_


`0.1.0 <https://github.com/ansys/pyresultexplorer/releases/tag/v0.1.0>`_ - September 02, 2026
=============================================================================================

.. tab-set::


  .. tab-item:: Added

    .. list-table::
        :header-rows: 0
        :widths: auto

        * - Feat: tech review
          - `#81 <https://github.com/ansys/pyresultexplorer/pull/81>`_

        * - Misc: improve install instructions, improve display options typing
          - `#107 <https://github.com/ansys/pyresultexplorer/pull/107>`_

        * - Pythonic plot and chart definition objects
          - `#117 <https://github.com/ansys/pyresultexplorer/pull/117>`_

        * - Feat: final release changes
          - `#153 <https://github.com/ansys/pyresultexplorer/pull/153>`_


  .. tab-item:: Fixed

    .. list-table::
        :header-rows: 0
        :widths: auto

        * - Fix: correct release-github SHA
          - `#113 <https://github.com/ansys/pyresultexplorer/pull/113>`_

        * - MCP support: fix subprocess STDIN issue & expose connection token property
          - `#143 <https://github.com/ansys/pyresultexplorer/pull/143>`_


  .. tab-item:: Documentation

    .. list-table::
        :header-rows: 0
        :widths: auto

        * - Doc: security
          - `#121 <https://github.com/ansys/pyresultexplorer/pull/121>`_

        * - Implement doc review feedback
          - `#125 <https://github.com/ansys/pyresultexplorer/pull/125>`_

        * - Chore: transfer to ansys org
          - `#131 <https://github.com/ansys/pyresultexplorer/pull/131>`_


  .. tab-item:: Dependencies

    .. list-table::
        :header-rows: 0
        :widths: auto

        * - Bump syrupy from 5.3.2 to 5.3.4
          - `#123 <https://github.com/ansys/pyresultexplorer/pull/123>`_

        * - Bump pre-commit from 4.6.0 to 4.6.1
          - `#139 <https://github.com/ansys/pyresultexplorer/pull/139>`_

        * - Bump playwright from 1.60.0 to 1.62.0
          - `#141 <https://github.com/ansys/pyresultexplorer/pull/141>`_

        * - Bump the pytest-dependencies group with 2 updates
          - `#145 <https://github.com/ansys/pyresultexplorer/pull/145>`_

        * - Update flit-core requirement from <4,>=3.12.0 to >=4.0.2,<5
          - `#146 <https://github.com/ansys/pyresultexplorer/pull/146>`_

        * - Bump pre-commit from 4.6.1 to 4.6.2
          - `#148 <https://github.com/ansys/pyresultexplorer/pull/148>`_

        * - Use released ansys-api-result-explorer pkg
          - `#152 <https://github.com/ansys/pyresultexplorer/pull/152>`_


  .. tab-item:: Maintenance

    .. list-table::
        :header-rows: 0
        :widths: auto

        * - Bump actions/checkout from 6.0.3 to 7.0.0 in the actions-deps group
          - `#108 <https://github.com/ansys/pyresultexplorer/pull/108>`_

        * - Add tests against released version
          - `#115 <https://github.com/ansys/pyresultexplorer/pull/115>`_

        * - Bump the actions-deps group across 1 directory with 13 updates
          - `#133 <https://github.com/ansys/pyresultexplorer/pull/133>`_

        * - Bump the actions-deps group with 13 updates
          - `#136 <https://github.com/ansys/pyresultexplorer/pull/136>`_

        * - Bump astral-sh/setup-uv from 8.3.2 to 9.0.0 in the actions-deps group
          - `#137 <https://github.com/ansys/pyresultexplorer/pull/137>`_

        * - Bump the actions-deps group with 11 updates
          - `#142 <https://github.com/ansys/pyresultexplorer/pull/142>`_

        * - Bump the actions-deps group across 1 directory with 12 updates
          - `#150 <https://github.com/ansys/pyresultexplorer/pull/150>`_


  .. tab-item:: Miscellaneous

    .. list-table::
        :header-rows: 0
        :widths: auto

        * - Bump soupsieve from 2.8 to 2.8.4
          - `#126 <https://github.com/ansys/pyresultexplorer/pull/126>`_

        * - Bump imageio from 2.37.3 to 2.37.4
          - `#135 <https://github.com/ansys/pyresultexplorer/pull/135>`_

        * - Fix: prevent test hang caused by missing client cleanup in test_connection_token_reconnect
          - `#144 <https://github.com/ansys/pyresultexplorer/pull/144>`_

        * - Bump pillow from 12.0.0 to 12.3.0
          - `#149 <https://github.com/ansys/pyresultexplorer/pull/149>`_


.. vale on
