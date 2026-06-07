// Core Module
const path     = require('path');
require('dotenv').config();

const express  = require('express');
const session  = require('express-session');
const MongoDBStore = require('connect-mongodb-session')(session);
const multer   = require('multer');
const cors     = require('cors');
const helmet   = require('helmet');
const mongoose = require('mongoose');
const DB_PATH  = process.env.MONGODB_URI || "mongodb://localhost:27017/ai_agent_skill";


const { router: authRouter, requireOnboard, requireAuth } = require("./routes/authRouter");
const { router: projectRouter } = require("./routes/projectRouter");
const aiRouter = require("./routes/aiRoutes")
const passwordResetRouter = require("./routes/passwordResetRoutes")
const emailVerificationRouter = require("./routes/emailVerificationRoutes") 
const rootDir = require("./utils/pathUtil");
const errorsController = require("./controllers/errors");
const { apiLimiter } = require('./middleware/rateLimiter');

const app = express();

// Trust proxy - required for Render deployment
app.set('trust proxy', 1);

// View engine setup
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));


app.use(helmet({
  contentSecurityPolicy: false,
  crossOriginEmbedderPolicy: false
}));

// Open CORS for local development/demo — allow all origins
app.use(cors({
  origin: true,
  credentials: true
}));


const randomString = (length) => {
  const characters = 'abcdefghijklmnopqrstuvwxyz';
  let result = '';
  for (let i = 0; i < length; i++) {
    result += characters.charAt(Math.floor(Math.random() * characters.length));
  }
  return result;
}

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, "uploads/");
  },
  filename: (req, file, cb) => {
    cb(null, randomString(10) + '-' + file.originalname);
  }
});

const fileFilter = (req, file, cb) => {
  if (file.mimetype === 'image/png' || file.mimetype === 'image/jpg' || file.mimetype === 'image/jpeg') {
    cb(null, true);
  } else {
    cb(null, false);
  }
}

const multerOptions = {
  storage, fileFilter
};

app.use(express.json()); 
app.use(express.urlencoded({ extended: true }));
app.use(multer(multerOptions).array('photos', 5)); 
app.use(express.static(path.join(rootDir, 'public')))
app.use("/uploads", express.static(path.join(rootDir, 'uploads')))
app.use("/host/uploads", express.static(path.join(rootDir, 'uploads')))
app.use("/homes/uploads", express.static(path.join(rootDir, 'uploads')))

let sessionStore;

app.use((req, res, next) => {
  const options = {
    secret: process.env.SESSION_SECRET || "KnowledgeGate AI with Complete Coding",
    resave: false,
    saveUninitialized: false,
    cookie: {
      maxAge: 1000 * 60 * 60 * 24 * 7, // 7 days
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: process.env.NODE_ENV === 'production' ? 'none' : 'lax'
    }
  };
  if (sessionStore) {
    options.store = sessionStore;
  }
  session(options)(req, res, next);
});



app.use((req, res, next) => {
  req.isLoggedIn = req.session.isLoggedIn
  next();
})

app.use('/api/', apiLimiter);

app.use(authRouter);
app.use('/api/password-reset', passwordResetRouter);
app.use('/api/verify-email', emailVerificationRouter);

// ── Landing page ──────────────────────────────────────────────────────────────
app.get('/', (req, res) => {
  if (req.session.isLoggedIn && req.session.user) {
    // Logged-in users go straight to their projects
    return res.redirect('/projects');
  }
  // Logged-out users see the landing page
  res.render('index');
});

// ── Project routes (protected) ────────────────────────────────────────────────
app.use(requireAuth);
app.use(requireOnboard);
app.use(projectRouter);
app.use(aiRouter);

app.use(errorsController.pageNotFound);

const PORT = process.env.PORT || 3010;

// ── DB connection with in-process fallback ────────────────────────────────────
async function startServer() {
  let dbUri = DB_PATH;

  try {
    await mongoose.connect(DB_PATH, { serverSelectionTimeoutMS: 5000 });
    console.log('MongoDB Atlas connected ✓');
    sessionStore = new MongoDBStore({
      uri: DB_PATH,
      collection: 'sessions'
    });
    sessionStore.on('error', (err) => console.error('Session store error:', err));
  } catch (atlasErr) {
    console.warn('⚠️  Atlas unavailable:', atlasErr.message);
    console.log('🔄 Starting in-process MongoDB (mongodb-memory-server)...');
    try {
      const { MongoMemoryServer } = require('mongodb-memory-server');
      const memServer = await MongoMemoryServer.create();
      dbUri = memServer.getUri();
      await mongoose.connect(dbUri);
      console.log('✅ In-process MongoDB running at', dbUri);
      console.log('ℹ️  Note: data will NOT persist after server restart (dev mode)');
      sessionStore = new MongoDBStore({
        uri: dbUri,
        collection: 'sessions'
      });
      sessionStore.on('error', (err) => console.error('Session store error:', err));
    } catch (memErr) {
      console.error('❌ Could not start in-process MongoDB:', memErr.message);
      console.log('Starting server without DB (session-only mode)...');
    }
  }

  app.listen(PORT, () => console.log(`Server running on address http://localhost:${PORT}`));
}

startServer();
