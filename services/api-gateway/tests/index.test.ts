import request from 'supertest';
import { app } from '../src/index';

describe('API Gateway', () => {
  describe('Health Checks', () => {
    it('GET /healthz should return healthy', async () => {
      const res = await request(app).get('/healthz');
      expect(res.status).toBe(200);
      expect(res.body.status).toBe('healthy');
    });
  });

  describe('404 Handler', () => {
    it('GET /unknown should return 404', async () => {
      const res = await request(app).get('/unknown-route');
      expect(res.status).toBe(404);
    });
  });
});
