# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import hashlib
import os

from odoo.tests.common import TransactionCase
from ..models import s3_helper

HASH_SPLIT = 2      # FIXME: testing implementations detail is not a good idea


class TestIrAttachment(TransactionCase):
    
    def _s3_object_exists(self, fname):
        access_key_id, secret_key, bucket_name, do_space_url, encryption_enabled = \
            s3_helper.parse_bucket_url(self.Attachment._storage())
        s3 = s3_helper.get_resource(access_key_id, secret_key, do_space_url)
        s3_bucket = self.Attachment._connect_to_S3_bucket(s3, bucket_name)
        return s3_helper.object_exists(s3, s3_bucket.name, fname)
        
    def setUp(self):
        super(TestIrAttachment, self).setUp()
        self.Attachment = self.env['ir.attachment']
        self.filestore = self.Attachment._filestore()
        
        # Blob1
        self.blob1 = b'blob1'
        self.blob1_b64 = base64.b64encode(self.blob1)
        blob1_hash = hashlib.sha1(self.blob1).hexdigest()
        self.blob1_fname = blob1_hash[:HASH_SPLIT] + '/' + blob1_hash

        # Blob2
        self.blob2 = b'blob2'
        self.blob2_b64 = base64.b64encode(self.blob2)

    def test_01_store_in_s3(self):
        schema = self.env['ir.config_parameter'].get_param('ir_attachment.location', '')
        self.assertEqual(schema[:5], 's3://')
 
        a1 = self.Attachment.create({'name': 'a1', 'datas': self.blob1_b64})
        self.assertEqual(a1.datas, self.blob1_b64)
 
        # not available in db
        a1_db_datas = a1.db_datas
        self.assertEqual(a1_db_datas, None)

        # available in s3
        self.assertEqual(self.blob1_b64, self.Attachment._file_read(a1.store_fname))
        
 
    def test_02_no_duplication(self):
        # Because odoo store file base on hash, the same content should create the 
        # same filename.
        a2 = self.Attachment.create({'name': 'a2', 'datas': self.blob1_b64})
        a3 = self.Attachment.create({'name': 'a3', 'datas': self.blob1_b64})
        self.assertEqual(a3.store_fname, a2.store_fname)

    def test_03_keep_file(self):
        a2 = self.Attachment.create({'name': 'a2', 'datas': self.blob1_b64})
        a3 = self.Attachment.create({'name': 'a3', 'datas': self.blob1_b64})
  
        a3.unlink()
        self.assertTrue(self._s3_object_exists(a2.store_fname))

    def test_04_change_data_change_file(self):
        a2 = self.Attachment.create({'name': 'a2', 'datas': self.blob1_b64})
        a2_store_fname1 = a2.store_fname
        #a2_fn = os.path.join(self.filestore, a2_store_fname1)
        self.assertTrue(self._s3_object_exists(a2_store_fname1))
        #self.assertTrue(os.path.isfile(a2_fn))
  
        a2.write({'datas': self.blob2_b64})
  
        a2_store_fname2 = a2.store_fname
        self.assertNotEqual(a2_store_fname1, a2_store_fname2)
  
        #a2_fn = os.path.join(self.filestore, a2_store_fname2)
        #self.assertTrue(os.path.isfile(a2_fn))
        self.assertTrue(self._s3_object_exists(a2_store_fname2))
