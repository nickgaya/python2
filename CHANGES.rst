Changelog
=========

1.2
---
- Update division operator to use classic division when dividing two Python 2
  objects, but true division for mixed Python 2 / 3 division.

- Update client to dynamically generate exception classes with special base
  types.

- Add special handling for ``TypeError``, allowing us to eliminate the awkward
  ``Py2Iterator`` wrapper.

- Test/build script improvements
    - Enable pytest-xdist
    - Docs support

- README improvements

1.1
---
- Changes to setup.py
- README improvements

1.0
---
- Initial release
