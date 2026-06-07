const express  = require('express');
const bcrypt   = require('bcryptjs');
const { check, validationResult } = require('express-validator');
const { normalizeEmail } = require('validator'); // same lib express-validator uses
const path     = require('path');
const Datastore = require('nedb-promises');
const router   = express.Router();

// ── NeDB persistent user store (file-based, no MongoDB needed) ─────────────
// Data is saved to disk → survives server restarts
const usersDB = Datastore.create({
    filename: path.join(__dirname, '..', 'data', 'users.db'),
    autoload: true,
});
// Ensure unique index on email
usersDB.ensureIndex({ fieldName: 'email', unique: true, sparse: true });

// ── Auth guard ────────────────────────────────────────────────────────────────
function requireAuth(req, res, next) {
    if (req.session.isLoggedIn && req.session.user) return next();
    return res.redirect('/login');
}

// ── Onboarding guard ──────────────────────────────────────────────────────────
function requireOnboard(req, res, next) {
    if (!req.session.isLoggedIn || !req.session.user) return res.redirect('/login');
    if (!req.session.user.onboarded) return res.redirect('/onboarding');
    return next();
}

// ── GET /login ────────────────────────────────────────────────────────────────
router.get('/login', (req, res) => {
    if (req.session.isLoggedIn) return res.redirect('/');
    res.render('auth/login', { error: null });
});

// ── POST /login ───────────────────────────────────────────────────────────────
router.post('/login', async (req, res) => {
    // Use the exact same normalizeEmail() that express-validator uses during signup.
    // This strips Gmail dots: "saurabh.rajput@gmail.com" → "saurabhrajput@gmail.com"
    // So the stored email always matches what we query here.
    const raw   = (req.body.email || '').trim();
    const email = normalizeEmail(raw) || raw.toLowerCase();
    const password = req.body.password;

    try {
        const user = await usersDB.findOne({ email });
        if (!user)
            return res.render('auth/login', { error: 'No account found with that email.' });

        const ok = await bcrypt.compare(password, user.password);
        if (!ok)
            return res.render('auth/login', { error: 'Incorrect password.' });

        req.session.isLoggedIn = true;
        req.session.user = {
            _id:             user._id,
            firstName:       user.firstName,
            lastName:        user.lastName  || '',
            email:           user.email,
            role:            user.role            || 'other',
            experienceLevel: user.experienceLevel || 'intermediate',
            goals:           user.goals           || '',
            onboarded:       true,
        };
        req.session.save((err) => {
            if (err) console.error('session save error:', err);
            res.redirect('/projects');
        });
    } catch (err) {
        console.error('login error:', err);
        res.render('auth/login', { error: 'Something went wrong. Please try again.' });
    }
});

// ── GET /signup ───────────────────────────────────────────────────────────────
router.get('/signup', (req, res) => {
    if (req.session.isLoggedIn) return res.redirect('/');
    res.render('auth/signup', { error: null, oldInput: {} });
});

// ── POST /signup ──────────────────────────────────────────────────────────────
router.post('/signup', [
    check('firstName').trim().isLength({ min: 2 }).withMessage('First name must be at least 2 characters.'),
    check('email').isEmail().withMessage('Enter a valid email.').normalizeEmail(),
    check('password').isLength({ min: 8 }).withMessage('Password must be at least 8 characters.'),
], async (req, res) => {
    const { firstName, lastName, email, password } = req.body;
    const errors = validationResult(req);
    if (!errors.isEmpty())
        return res.render('auth/signup', { error: errors.array()[0].msg, oldInput: { firstName, lastName, email } });

    try {
        const existing = await usersDB.findOne({ email });
        if (existing)
            return res.render('auth/signup', { error: 'An account with this email already exists.', oldInput: { firstName, lastName, email } });

        const hashed = await bcrypt.hash(password, 12);
        const user   = await usersDB.insert({
            firstName,
            lastName:        lastName || '',
            email,
            password:        hashed,
            authProvider:    'local',
            role:            'other',
            experienceLevel: 'intermediate',
            goals:           '',
            onboarded:       true,
            createdAt:       new Date(),
        });

        req.session.isLoggedIn = true;
        req.session.user = {
            _id:             user._id,
            firstName:       user.firstName,
            lastName:        user.lastName  || '',
            email:           user.email,
            role:            'other',
            experienceLevel: 'intermediate',
            goals:           '',
            onboarded:       true,
        };
        req.session.save((err) => {
            if (err) console.error('session save error:', err);
            res.redirect('/projects');
        });
    } catch (err) {
        console.error('signup error:', err);
        const errMsg = err.errorType === 'uniqueViolated'
            ? 'An account with this email already exists.'
            : 'Could not create account. Please try again.';
        res.render('auth/signup', { error: errMsg, oldInput: { firstName, lastName, email } });
    }
});

// ── GET /onboarding ───────────────────────────────────────────────────────────
router.get('/onboarding', requireAuth, (req, res) => {
    res.render('onboarding', { userName: req.session.user.firstName });
});

// ── POST /onboarding ──────────────────────────────────────────────────────────
router.post('/onboarding', requireAuth, async (req, res) => {
    const { role, goals, level } = req.body;
    try {
        await usersDB.update(
            { _id: req.session.user._id },
            { $set: {
                role:            role  || 'other',
                goals:           goals || '',
                experienceLevel: level || 'intermediate',
                onboarded:       true,
            }}
        );
        req.session.user.role            = role  || 'other';
        req.session.user.goals           = goals || '';
        req.session.user.experienceLevel = level || 'intermediate';
        req.session.user.onboarded       = true;
        await req.session.save();
    } catch (err) {
        console.error('onboarding error:', err);
    }
    res.redirect('/');
});

// ── GET /logout ───────────────────────────────────────────────────────────────
router.get('/logout', (req, res) => {
    req.session.destroy(() => res.redirect('/login'));
});

module.exports = { router, requireAuth, requireOnboard };
