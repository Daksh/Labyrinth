# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""Simplify tarfile module usage"""

import os
import time
import tarfile
import cStringIO
import gtk
import zipfile
import tempfile
import shutil

class TarballError(Exception):
    """Base Tarball exception."""
    pass

class BadDataTypeError(TarballError):
    """Exception for unsupported data type in read/write methods."""
    pass

class Tarball:
    """
    Wrap standart tarfile module to simplify read/write operations with
    most popular data types.

    In read mode Tarball can load zip files as well.

    Supprted types:

        * string
        * gtk.gdk.Pixbuf

    Write usage:

        # create Tarball object
        # to see all supported modes use
        # http://docs.python.org/library/tarfile.html#tarfile.open
        tar = Tarball(tarfile, 'w')

        # write string to file in tarball
        tar.write('name within tarball', 'string to write')

        # write pixbuf to file in tarball
        tar.write('name within tarball', pixbuf_object)

        # save and close tarball file
        tar.close()

    Read usage:

        # create Tarball object
        tar = Tarball(tarfile)

        # read content of file in tarball to string
        str_content = tar.read('name within tarball')

        # read content of file in tarball to pixbuf object
        pixbuf_content = tar.read_pixbuf('name within tarball')
    """

    def __init__(self, name=None, mode='r', mtime=None):
        if not mode.startswith('r') or tarfile.is_tarfile(name):
            self.__tar = tarfile.TarFile(name=name, mode=mode)
        else:
            # convert for tar

            if not zipfile.is_zipfile(name):
                raise tarfile.ReadError()

            try:
                tmp_dir = tempfile.mkdtemp()
                tmp_fd, tmp_name = tempfile.mkstemp()
                tmp_fo = os.fdopen(tmp_fd, 'w')

                zip = zipfile.ZipFile(name)
                zip.extractall(tmp_dir)

                tar = tarfile.TarFile(fileobj=tmp_fo, mode='w')
                tar.add(tmp_dir, arcname='')
                tar.close()

                self.__tar = tarfile.TarFile(name=tmp_name, mode=mode)
            finally:
                tmp_fo.close()
                os.unlink(tmp_name)
                shutil.rmtree(tmp_dir)

        if mtime:
            self.mtime = mtime
        else:
            self.mtime = time.time()

    def close(self):
        """Save(if 'r' mode was given) and close tarball file."""
        self.__tar.close()

    def getnames(self):
        """Return names of members sorted by creation order."""
        return self.__tar.getnames()

    def read(self, arcname):
        """Returns sring with content of given file from tarball."""
        file_o = self.__tar.extractfile(arcname.encode('utf8'))
        if not file_o:
            return None
        out = file_o.read()
        file_o.close()
        return out

    def read_pixbuf(self, arcname):
        """Returns pixbuf object of given file from tarball."""
        loader = gtk.gdk.pixbuf_loader_new_with_mime_type('image/png')
        loader.write(self.read(arcname))
        loader.close()
        return loader.get_pixbuf()

    def write(self, arcname, data, mode=0644):
        """
        Stores given object to file in tarball.
        Raises BadDataTypeError exception If data type isn't supported.
        """
        info = tarfile.TarInfo(arcname.encode('utf8'))
        info.mode = mode
        info.mtime = self.mtime

        if isinstance(data, str):
            self.__write_str(info, data)
        elif isinstance(data, gtk.gdk.Pixbuf):
            self.__write_pixbuf(info, data)
        else:
            raise BadDataTypeError()

    def __write_str(self, info, data):
        info.size = len(data)
        self.__tar.addfile(info, cStringIO.StringIO(data))
        
    def __write_pixbuf(self, info, data):
        def push(pixbuf, buffer):
            buffer.write(pixbuf)

        buffer = cStringIO.StringIO()
        data.save_to_callback(push, 'png', user_data=buffer)

        info.size = buffer.tell()
        buffer.seek(0)
        self.__tar.addfile(info, buffer)
