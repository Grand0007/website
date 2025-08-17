import React, { useState } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  IconButton,
  Menu,
  MenuItem,
  Avatar,
  Box,
  useTheme,
  useMediaQuery,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  CloudUpload as UploadIcon,
  Description as ResumesIcon,
  Person as ProfileIcon,
  Logout as LogoutIcon,
  Home as HomeIcon,
  SmartToy as AIIcon
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

const Navbar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  
  const [anchorEl, setAnchorEl] = useState(null);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);

  const handleUserMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleUserMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = async () => {
    await logout();
    handleUserMenuClose();
    navigate('/');
  };

  const handleNavigation = (path) => {
    navigate(path);
    setMobileDrawerOpen(false);
    handleUserMenuClose();
  };

  // Navigation items for authenticated users
  const navItems = [
    { label: 'Dashboard', path: '/dashboard', icon: <DashboardIcon /> },
    { label: 'Upload Resume', path: '/upload', icon: <UploadIcon /> },
    { label: 'My Resumes', path: '/resumes', icon: <ResumesIcon /> },
  ];

  // User menu items
  const userMenuItems = [
    { label: 'Profile', path: '/profile', icon: <ProfileIcon /> },
    { label: 'Dashboard', path: '/dashboard', icon: <DashboardIcon /> },
    { label: 'My Resumes', path: '/resumes', icon: <ResumesIcon /> },
  ];

  // Mobile drawer content
  const drawerContent = (
    <Box sx={{ width: 250, pt: 2 }}>
      <Box sx={{ px: 2, pb: 2 }}>
        <Typography variant="h6" color="primary" fontWeight="bold">
          AI Resume Updater
        </Typography>
      </Box>
      <Divider />
      
      {user ? (
        <>
          <List>
            {navItems.map((item) => (
              <ListItem 
                button 
                key={item.path}
                onClick={() => handleNavigation(item.path)}
                selected={location.pathname === item.path}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={item.label} />
              </ListItem>
            ))}
          </List>
          <Divider />
          <List>
            <ListItem button onClick={() => handleNavigation('/profile')}>
              <ListItemIcon><ProfileIcon /></ListItemIcon>
              <ListItemText primary="Profile" />
            </ListItem>
            <ListItem button onClick={handleLogout}>
              <ListItemIcon><LogoutIcon /></ListItemIcon>
              <ListItemText primary="Logout" />
            </ListItem>
          </List>
        </>
      ) : (
        <List>
          <ListItem button onClick={() => handleNavigation('/')}>
            <ListItemIcon><HomeIcon /></ListItemIcon>
            <ListItemText primary="Home" />
          </ListItem>
          <ListItem button onClick={() => handleNavigation('/login')}>
            <ListItemIcon><ProfileIcon /></ListItemIcon>
            <ListItemText primary="Login" />
          </ListItem>
        </List>
      )}
    </Box>
  );

  return (
    <>
      <AppBar position="fixed" elevation={1}>
        <Toolbar>
          {/* Mobile menu button */}
          {isMobile && (
            <IconButton
              edge="start"
              color="inherit"
              aria-label="menu"
              onClick={() => setMobileDrawerOpen(true)}
              sx={{ mr: 2 }}
            >
              <MenuIcon />
            </IconButton>
          )}

          {/* Logo */}
          <Box 
            sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              cursor: 'pointer',
              flexGrow: isMobile ? 1 : 0 
            }}
            onClick={() => navigate(user ? '/dashboard' : '/')}
          >
            <AIIcon sx={{ mr: 1 }} />
            <Typography variant="h6" component="div" fontWeight="bold">
              AI Resume Updater
            </Typography>
          </Box>

          {/* Desktop navigation */}
          {!isMobile && (
            <Box sx={{ flexGrow: 1, display: 'flex', ml: 4 }}>
              {user && navItems.map((item) => (
                <Button
                  key={item.path}
                  color="inherit"
                  onClick={() => handleNavigation(item.path)}
                  sx={{
                    mx: 1,
                    borderBottom: location.pathname === item.path ? 2 : 0,
                    borderColor: 'white',
                    borderRadius: 0,
                  }}
                >
                  {item.label}
                </Button>
              ))}
            </Box>
          )}

          {/* User section */}
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            {user ? (
              <>
                {!isMobile && (
                  <Typography variant="body2" sx={{ mr: 2 }}>
                    Welcome, {user.first_name}
                  </Typography>
                )}
                <IconButton
                  onClick={handleUserMenuOpen}
                  color="inherit"
                  aria-label="user menu"
                >
                  <Avatar 
                    sx={{ 
                      bgcolor: theme.palette.secondary.main,
                      width: 32,
                      height: 32,
                      fontSize: '0.875rem'
                    }}
                  >
                    {user.first_name?.[0]?.toUpperCase() || 'U'}
                  </Avatar>
                </IconButton>
              </>
            ) : (
              !isMobile && (
                <Button 
                  color="inherit" 
                  onClick={() => navigate('/login')}
                  variant="outlined"
                  sx={{ 
                    borderColor: 'white',
                    '&:hover': {
                      borderColor: 'white',
                      backgroundColor: 'rgba(255,255,255,0.1)'
                    }
                  }}
                >
                  Login
                </Button>
              )
            )}
          </Box>
        </Toolbar>
      </AppBar>

      {/* User menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleUserMenuClose}
        PaperProps={{
          sx: { mt: 1, minWidth: 200 }
        }}
      >
        {user && (
          <Box sx={{ px: 2, py: 1, borderBottom: 1, borderColor: 'divider' }}>
            <Typography variant="subtitle2" fontWeight="bold">
              {user.first_name} {user.last_name}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {user.email}
            </Typography>
          </Box>
        )}
        
        {userMenuItems.map((item) => (
          <MenuItem
            key={item.path}
            onClick={() => handleNavigation(item.path)}
          >
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              {item.icon}
              <Typography sx={{ ml: 1 }}>{item.label}</Typography>
            </Box>
          </MenuItem>
        ))}
        
        <Divider />
        <MenuItem onClick={handleLogout}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <LogoutIcon />
            <Typography sx={{ ml: 1 }}>Logout</Typography>
          </Box>
        </MenuItem>
      </Menu>

      {/* Mobile drawer */}
      <Drawer
        anchor="left"
        open={mobileDrawerOpen}
        onClose={() => setMobileDrawerOpen(false)}
      >
        {drawerContent}
      </Drawer>
    </>
  );
};

export default Navbar;