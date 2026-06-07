const express  = require('express');
const path     = require('path');
const Datastore = require('nedb-promises');
const router   = express.Router();

// ── NeDB persistent project store ─────────────────────────────────────────────
const projectsDB = Datastore.create({
    filename: path.join(__dirname, '..', 'data', 'projects.db'),
    autoload: true,
});
projectsDB.ensureIndex({ fieldName: 'userId' });

// ── GET /projects — list user's projects ──────────────────────────────────────
router.get('/projects', async (req, res) => {
    try {
        const projects = await projectsDB.find({ userId: req.session.user._id })
            .sort ? (await projectsDB.find({ userId: req.session.user._id })) : [];
        const sorted = projects.sort((a,b) => new Date(b.createdAt) - new Date(a.createdAt));
        res.render('projects', {
            userName:    req.session.user.firstName,
            userRole:    req.session.user.role || 'other',
            userLevel:   req.session.user.experienceLevel || 'intermediate',
            currentPage: 'projects',
            projects:    sorted,
        });
    } catch(err) {
        console.error('projects error:', err);
        res.render('projects', { userName: req.session.user.firstName, userRole: 'other', userLevel: 'intermediate', currentPage: 'projects', projects: [] });
    }
});

// ── GET /favourites — list user's favourite projects ──────────────────────────
router.get('/favourites', async (req, res) => {
    try {
        const projects = await projectsDB.find({ userId: req.session.user._id, isFavourite: true });
        const sorted = projects.sort((a,b) => new Date(b.createdAt) - new Date(a.createdAt));
        res.render('favourites', {
            userName:    req.session.user.firstName,
            userRole:    req.session.user.role || 'other',
            userLevel:   req.session.user.experienceLevel || 'intermediate',
            currentPage: 'favourites',
            projects:    sorted,
        });
    } catch(err) {
        console.error('favourites error:', err);
        res.render('favourites', { userName: req.session.user.firstName, userRole: 'other', userLevel: 'intermediate', currentPage: 'favourites', projects: [] });
    }
});

// ── GET /projects/:id — single project detail ─────────────────────────────────
router.get('/projects/:id', async (req, res) => {
    try {
        const project = await projectsDB.findOne({ _id: req.params.id, userId: req.session.user._id });
        if (!project) return res.redirect('/projects');
        res.render('project-detail', {
            userName:    req.session.user.firstName,
            userRole:    req.session.user.role || 'other',
            userLevel:   req.session.user.experienceLevel || 'intermediate',
            currentPage: 'projects',
            project,
        });
    } catch(err) {
        res.redirect('/projects');
    }
});

// ── POST /api/projects/save — save AI response as project ────────────────────
router.post('/api/projects/save', async (req, res) => {
    const { title, prompt, response } = req.body;
    if (!prompt || !response) return res.json({ success: false, error: 'Missing fields' });
    try {
        const project = await projectsDB.insert({
            userId:      req.session.user._id,
            title:       title || prompt.slice(0, 60) + (prompt.length > 60 ? '...' : ''),
            prompt,
            response,
            isFavourite: false,
            createdAt:   new Date(),
        });
        res.json({ success: true, project });
    } catch(err) {
        res.json({ success: false, error: err.message });
    }
});

// ── POST /api/projects/:id/favourite — toggle favourite ──────────────────────
router.post('/api/projects/:id/favourite', async (req, res) => {
    try {
        const project = await projectsDB.findOne({ _id: req.params.id, userId: req.session.user._id });
        if (!project) return res.json({ success: false });
        await projectsDB.update({ _id: req.params.id }, { $set: { isFavourite: !project.isFavourite } });
        res.json({ success: true, isFavourite: !project.isFavourite });
    } catch(err) {
        res.json({ success: false, error: err.message });
    }
});

// ── DELETE /api/projects/:id — delete a project ───────────────────────────────
router.delete('/api/projects/:id', async (req, res) => {
    try {
        await projectsDB.remove({ _id: req.params.id, userId: req.session.user._id });
        res.json({ success: true });
    } catch(err) {
        res.json({ success: false, error: err.message });
    }
});

module.exports = { router, projectsDB };
