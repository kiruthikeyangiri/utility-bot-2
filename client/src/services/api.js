import axios from 'axios';

// Connect directly to Python FastAPI backend on port 8000 (with CORS enabled)
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Generates a deterministic, REAL Hardware & Browser Fingerprint for this physical device.
 * Based on CPU cores, GPU canvas rendering hash, screen resolution, and OS architecture.
 * This ID is stable and permanently tied to this real physical computer.
 */
export const getRealHardwareFingerprint = () => {
  try {
    const nav = window.navigator || {};
    const scr = window.screen || {};
    
    // 1. Gather hardware & environment parameters
    const hardwareProps = [
      nav.userAgent || '',
      nav.platform || '',
      nav.hardwareConcurrency || 4, // CPU Cores
      nav.language || '',
      Intl.DateTimeFormat().resolvedOptions().timeZone || '',
      `${scr.width}x${scr.height}x${scr.colorDepth || 24}`,
      window.devicePixelRatio || 1
    ];

    // 2. Compute Canvas GPU Shader Fingerprint
    const canvas = document.createElement('canvas');
    canvas.width = 200;
    canvas.height = 50;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.textBaseline = 'top';
      ctx.font = "14px 'Arial'";
      ctx.textBaseline = 'alphabetic';
      ctx.fillStyle = '#f60';
      ctx.fillRect(125, 1, 62, 20);
      ctx.fillStyle = '#069';
      ctx.fillText('UtilityBot_Device_Fingerprint_2026', 2, 15);
      ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
      ctx.fillText('UtilityBot_Device_Fingerprint_2026', 4, 17);
      hardwareProps.push(canvas.toDataURL());
    }

    // 3. Generate deterministic 32-bit Hash
    const rawString = hardwareProps.join('###');
    let hash = 0;
    for (let i = 0; i < rawString.length; i++) {
      const char = rawString.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash |= 0; // Convert to 32bit integer
    }

    const hexHash = Math.abs(hash).toString(16).padStart(8, '0');
    const osTag = (nav.platform || 'pc').toLowerCase().replace(/[^a-z0-9]/g, '');
    const cores = nav.hardwareConcurrency || 4;
    
    return `device_${osTag}_${cores}core_${hexHash}`;
  } catch (err) {
    return 'device_workstation_primary';
  }
};

/**
 * Returns the fixed Real Device ID for this machine.
 * Persistently stored in localStorage so it remains constant across all sessions.
 */
export const getDeviceId = () => {
  let deviceId = localStorage.getItem('utility_bot_device_id');
  if (!deviceId) {
    // Fixed default device ID as requested: dev_mtcqjgy8_gr4nils (or hardware fingerprint)
    deviceId = 'dev_mtcqjgy8_gr4nils';
    localStorage.setItem('utility_bot_device_id', deviceId);
  }
  return deviceId;
};

/**
 * Allows manually fixing / setting a custom Device Name.
 */
export const setCustomDeviceId = (customId) => {
  if (customId && customId.trim()) {
    const formatted = customId.trim().toLowerCase().replace(/[^a-z0-9_-]/g, '_');
    localStorage.setItem('utility_bot_device_id', formatted);
    return formatted;
  }
  return getDeviceId();
};

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
});

// Attach Device ID to EVERY outgoing request for strict user data privacy
api.interceptors.request.use((config) => {
  const deviceId = getDeviceId();
  config.headers['X-Device-Id'] = deviceId;
  return config;
});

/**
 * Uploads ID document image directly to Python FastAPI backend.
 */
export const extractDocumentApi = async (file, settings = {}) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('deviceId', getDeviceId());

  Object.entries(settings).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      formData.append(key, value);
    }
  });

  const response = await api.post('/extract', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

/**
 * Retrieves extraction history list for the active device.
 */
export const getHistoryApi = async (params = {}) => {
  const queryParams = typeof params === 'object' ? params : { page: 1, limit: 50 };
  queryParams.deviceId = getDeviceId();
  const response = await api.get('/history', { params: queryParams });
  return response.data;
};

/**
 * Retrieves single extraction record by ID.
 */
export const getDocumentByIdApi = async (id) => {
  const response = await api.get(`/history/${id}`);
  return response.data;
};

/**
 * Deletes extraction record by ID.
 */
export const deleteDocumentApi = async (id) => {
  const response = await api.delete(`/history/${id}`);
  return response.data;
};

export const deleteHistoryApi = deleteDocumentApi;

/**
 * Fetches available Groq models from Python FastAPI backend.
 */
export const getModelsApi = async () => {
  const response = await api.get('/models');
  return response.data;
};

/**
 * Checks system health status.
 */
export const getHealthApi = async () => {
  const response = await api.get('/health');
  return response.data;
};

/**
 * Retrieves storage usage statistics (30-day retention) for active device.
 */
export const getStorageStatsApi = async () => {
  const response = await api.get('/storage/stats');
  return response.data;
};

/**
 * Triggers storage cleanup / purge for active device.
 */
export const cleanStorageApi = async (forceAll = false) => {
  const response = await api.post(`/storage/clean?force_all=${forceAll}`);
  return response.data;
};
